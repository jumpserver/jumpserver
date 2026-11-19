"""User MCP authorizations, independent of the selected organization."""
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import get_application_model
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from authentication.services.agent_clients import agent_oauth_bindings, revoke_user_agent_client
from common.drf.filters import SearchFilter
from common.permissions import IsValidUser
from common.utils import get_request_ip
from orgs.models import Organization
from terminal.models import AgentApplication, AgentOAuthBinding

__all__ = ['UserAgentClientViewSet']


def record_client_operation(request, operation, client, result):
    create_or_update_operate_log(
        operation,
        _('Agent MCP client'),
        force=True,
        resource_id=str(client['id']),
        resource_display=(
            f"{client['name']} ({client['client_id']})" if client['client_id'] else client['name']
        ),
        user=request.user,
        org_id=Organization.SYSTEM_ID,
        remote_addr=get_request_ip(request),
        after={
            'Client ID': {'name': 'client_id', 'value': client['client_id']},
            'Result': {'name': 'result', 'value': result},
        },
    )


class UserAgentClientSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(read_only=True, label=_('Client ID'))
    status = serializers.SerializerMethodField(label=_('Status'))
    expires_at = serializers.SerializerMethodField(label=_('Expiration date'))

    class Meta:
        model = get_application_model()
        fields = ('id', 'name', 'client_id', 'status', 'expires_at')
        read_only_fields = fields

    def get_status(self, obj):
        return 'active' if any(binding.is_live for binding in obj.user_bindings) else 'expired'

    def get_expires_at(self, obj):
        deadline = max((binding.expires_at for binding in obj.user_bindings if binding.is_live), default=None)
        if deadline is None:
            deadline = max((binding.expires_at for binding in obj.user_bindings), default=None)
        return deadline.isoformat() if deadline else None


class UserAgentClientPagination(LimitOffsetPagination):
    default_limit = 20
    max_limit = 100


class UserAgentClientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, GenericViewSet):
    serializer_class = UserAgentClientSerializer
    permission_classes = [IsValidUser]
    http_method_names = ['get', 'head', 'options', 'post']
    filter_backends = [SearchFilter]
    search_fields = ('name', 'client_id')
    pagination_class = UserAgentClientPagination

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'no-store'
        return response

    def get_queryset(self):
        user = self.request.user
        bindings = agent_oauth_bindings().filter(user=user)
        return get_application_model().objects.filter(
            pk__in=bindings.values('application_id'), agent_registration__isnull=False,
        ).prefetch_related(
            Prefetch('agentoauthbinding_set', queryset=bindings, to_attr='user_bindings'),
        ).order_by('-created', '-pk')

    @action(methods=['post'], detail=True)
    def revoke(self, request, *args, **kwargs):
        client = self.get_object()
        with transaction.atomic():
            # Match token issuance's application-first lock order. A refresh
            # validated before this revocation must not restore its binding.
            application = get_object_or_404(
                get_application_model().objects.select_for_update(), pk=client.pk
            )
            registration = get_object_or_404(
                AgentApplication.objects.select_for_update(), application=application
            )
            if not AgentOAuthBinding.objects.filter(
                user=request.user, application=application
            ).exists():
                raise NotFound()
            client_info = {
                'id': registration.pk,
                'name': application.name,
                'client_id': application.client_id,
            }
            recycled = revoke_user_agent_client(request.user, application, registration)
            result = 'revoked only the current user authorizations in all organizations'
            if recycled:
                result += '; removed unused client registration'
            record_client_operation(request, ActionChoices.update, client_info, result)
        return Response(status=status.HTTP_204_NO_CONTENT)
