"""User MCP authorizations, independent of the selected organization."""
from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import (
    get_application_model, get_refresh_token_model, refresh_token_expire_timedelta,
)
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from authentication.services.agent_clients import revoke_user_agent_client
from common.drf.filters import SearchFilter
from common.permissions import IsValidUser
from common.utils import get_request_ip
from orgs.models import Organization
from terminal.agent_service import ALL_AGENT_ORGANIZATIONS, available_agent_organizations
from terminal.models import AgentApplication, AgentOAuthBinding

__all__ = ['UserAgentClientViewSet']


def record_client_operation(request, action, client, result):
    create_or_update_operate_log(
        action, _('Agent MCP client'), force=True,
        resource_id=str(client['id']),
        resource_display=f"{client['name']} ({client['client_id']})" if client['client_id'] else client['name'],
        user=request.user, org_id=Organization.SYSTEM_ID, remote_addr=get_request_ip(request),
        after={
            'Client ID': {'name': 'client_id', 'value': client['client_id']},
            'Result': {'name': 'result', 'value': result},
        },
    )


class UserAgentClientSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(read_only=True, label=_('Client ID'))
    organizations = serializers.SerializerMethodField(label=_('Organizations'))
    all_organizations = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField(label=_('Status'))

    class Meta:
        model = get_application_model()
        fields = ('id', 'name', 'client_id', 'organizations', 'all_organizations', 'status')
        read_only_fields = fields

    def get_all_organizations(self, obj):
        return any(str(binding.org_id) == ALL_AGENT_ORGANIZATIONS for binding in self.live_bindings(obj))

    @staticmethod
    def live_bindings(obj):
        now = timezone.now()
        return [binding for binding in obj.user_bindings if (
            binding.has_refresh or (binding.grant_id and binding.grant.expires > now)
            or (binding.access_token_id and binding.access_token.expires > now and (
                not getattr(binding.access_token, 'refresh_token', None)
                or binding.access_token.refresh_token.revoked is None
            ))
        )]

    def get_organizations(self, obj):
        return self.context['view'].available_organizations if self.get_all_organizations(obj) else []

    def get_status(self, obj):
        if not obj.agent_registration.is_active:
            return 'disabled'
        return 'active' if self.get_organizations(obj) else 'expired'


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

    @cached_property
    def available_organizations(self):
        return [
            {'id': str(org.pk), 'name': org.name}
            for org in available_agent_organizations(self.request.user)
        ]

    def get_queryset(self):
        user = self.request.user
        refresh = get_refresh_token_model().objects.filter(
            user=user, application_id=OuterRef('application_id'), token_family=OuterRef('refresh_family'),
            revoked__isnull=True, access_token__isnull=False,
        )
        lifetime = refresh_token_expire_timedelta()
        if lifetime:
            refresh = refresh.filter(access_token__expires__gt=timezone.now() - lifetime)
        bindings = AgentOAuthBinding.objects.filter(user=user).select_related(
            'access_token__refresh_token', 'grant',
        ).defer('access_token__token', 'access_token__refresh_token__token', 'grant__code').annotate(has_refresh=Exists(refresh))
        return get_application_model().objects.filter(
            pk__in=bindings.values('application_id'), agent_registration__isnull=False,
        ).select_related('agent_registration').prefetch_related(
            Prefetch('agentoauthbinding_set', queryset=bindings, to_attr='user_bindings'),
        ).order_by('-created', '-pk')

    @action(methods=['post'], detail=True)
    def revoke(self, request, *args, **kwargs):
        client = self.get_object()
        with transaction.atomic():
            # Match token issuance's application-first lock order. A refresh
            # validated before this revocation must not restore its binding.
            application = get_object_or_404(get_application_model().objects.select_for_update(), pk=client.pk)
            registration = get_object_or_404(AgentApplication.objects.select_for_update(), application=application)
            client_info = {'id': registration.pk, 'name': application.name, 'client_id': application.client_id}
            recycled = revoke_user_agent_client(request.user, application, registration)
            result = 'revoked only the current user authorizations in all organizations'
            if recycled:
                result += '; removed unused client registration'
            record_client_operation(request, ActionChoices.update, client_info, result)
        return Response(status=status.HTTP_204_NO_CONTENT)
