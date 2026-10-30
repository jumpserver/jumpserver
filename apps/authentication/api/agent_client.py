from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_grant_model, get_refresh_token_model,
)
from rest_framework import mixins, serializers, status
from rest_framework.decorators import action
from rest_framework.response import Response

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from authentication.services.agent_clients import (
    AgentClientCleanupBusy, AgentClientCleanupUnavailable, cleanup_agent_oauth_clients,
)
from common.api import JMSGenericViewSet
from common.drf.filters import LookupFilterBackend, SearchFilter
from common.permissions import IsValidUser
from common.utils import get_request_ip
from orgs.models import Organization
from rbac.models import Role
from terminal.models import AgentApplication, AgentOAuthBinding

__all__ = ['AgentClientViewSet']


class AgentClientAdminPermission(IsValidUser):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        # A client may have grants in multiple organizations. Organization roles
        # must never grant authority to manage the shared registration.
        permissions = Role.get_scope_roles_perms(
            list(request.user.system_roles.all()), Role.Scope.system,
        )
        return permissions.filter(content_type__app_label='settings', codename='change_auth').exists()


class AgentClientSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='application.name', read_only=True, label=_('Name'))
    client_id = serializers.CharField(source='application.client_id', read_only=True, label=_('Client ID'))
    created = serializers.DateTimeField(source='application.created', read_only=True, label=_('Date created'))
    is_active = serializers.BooleanField(read_only=True, label=_('Active'))
    date_authorized = serializers.DateTimeField(read_only=True, allow_null=True, label=_('First authorized'))

    class Meta:
        model = AgentApplication
        fields = ('id', 'name', 'client_id', 'is_active', 'created', 'date_authorized')
        read_only_fields = fields


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


class AgentClientViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, JMSGenericViewSet):
    queryset = AgentApplication.objects.select_related('application').order_by('-application__created', '-pk')
    serializer_class = AgentClientSerializer
    permission_classes = [AgentClientAdminPermission]
    http_method_names = ['get', 'head', 'options', 'post', 'delete']
    filter_backends = [LookupFilterBackend, SearchFilter]
    filterset_fields = ('is_active',)
    search_fields = ['application__name', 'application__client_id']

    def destroy(self, request, *args, **kwargs):
        registration = self.get_object()
        with transaction.atomic():
            # Serialize with authorization and token issuance before revoking grants.
            application = get_object_or_404(
                get_application_model().objects.select_for_update(), pk=registration.application_id,
            )
            registration = get_object_or_404(AgentApplication.objects.select_for_update(), pk=registration.pk)
            client = {'id': registration.pk, 'name': application.name, 'client_id': application.client_id}
            AgentApplication.objects.filter(pk=registration.pk).update(is_active=False)
            for model in (get_refresh_token_model(), get_access_token_model(), get_grant_model(), AgentOAuthBinding):
                model.objects.filter(application=application).delete()
            try:
                with transaction.atomic():
                    application.delete()
            except ProtectedError:
                # Audit rows keep the OAuth application identity. Remove its
                # registration and callbacks so it cannot authorize again.
                application.redirect_uris = ''
                application.save(update_fields=['redirect_uris'])
                registration.delete()
            record_client_operation(request, ActionChoices.delete, client, 'removed client and revoked authorizations')
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post'], detail=True)
    def disable(self, request, *args, **kwargs):
        return self._set_active(request, False)

    @action(methods=['post'], detail=True)
    def enable(self, request, *args, **kwargs):
        return self._set_active(request, True)

    def _set_active(self, request, active):
        registration = self.get_object()
        with transaction.atomic():
            # Match authorization and cleanup lock order.
            application = get_object_or_404(
                get_application_model().objects.select_for_update(), pk=registration.application_id,
            )
            registration = get_object_or_404(AgentApplication.objects.select_for_update(), pk=registration.pk)
            was_active = registration.is_active
            AgentApplication.objects.filter(pk=registration.pk).update(is_active=active)
            registration.is_active = active
            registration.application = application
            state = 'enabled' if active else 'disabled'
            record_client_operation(request, ActionChoices.update, {
                'id': registration.pk, 'name': application.name, 'client_id': application.client_id,
            }, state if was_active != active else f'already {state}')
        return Response(self.get_serializer(registration).data)

    @action(methods=['post'], detail=False)
    def cleanup(self, request, *args, **kwargs):
        try:
            result = cleanup_agent_oauth_clients(on_delete=lambda client: record_client_operation(
                request, ActionChoices.delete, client, 'removed unused registration',
            ))
        except AgentClientCleanupBusy:
            return Response({'detail': _('Client registration or cleanup is busy; try again later.')},
                            status=status.HTTP_409_CONFLICT)
        except AgentClientCleanupUnavailable:
            return Response({'detail': _('Client cleanup is temporarily unavailable; try again later.')},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        record_client_operation(request, ActionChoices.delete, {
            'id': '', 'name': _('Unused Agent MCP clients'), 'client_id': '',
        }, f"scanned={result['scanned']}, deleted={result['deleted']}, skipped={result['skipped']}")
        return Response(result)
