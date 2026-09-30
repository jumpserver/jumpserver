import base64
import hashlib
import hmac
import uuid
from email.utils import parsedate_to_datetime

from accounts import serializers
from accounts.const import AuditEvent
from accounts.credential_rotation import CredentialRotationManager
from accounts.mixins import ApplicationAuditMixin
from accounts.models import (
    ApplicationCredential,
    CredentialApplicationBinding,
    CredentialClientInstance,
)
from accounts.permissions import IsCredentialClient
from authentication.backends.drf import (
    CredentialAgentAuthentication,
    ServiceAuthentication,
)
from common.api import JMSGenericViewSet
from common.exceptions import JMSException
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from rest_framework import mixins, status
from rest_framework import serializers as drf_serializers
from rest_framework.decorators import action
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response

from common.utils import get_request_ip

__all__ = [
    'ApplicationCredentialViewSet', 'CredentialApplicationBindingViewSet',
    'CredentialClientInstanceViewSet', 'CredentialClientViewSet',
]


CREDENTIAL_CLIENT_SIGNATURE_HEADERS = [
    '(request-target)', 'date', 'digest', 'x-jms-request-id', 'x-jms-client-version',
    'x-jms-protocol-version', 'x-jms-config-schema-version',
]


class CredentialEventQuerySerializer(drf_serializers.Serializer):
    client_id = drf_serializers.UUIDField(required=False)
    rotation_id = drf_serializers.UUIDField(required=False)
    cycle_id = drf_serializers.UUIDField(required=False)
    limit = drf_serializers.IntegerField(default=20, min_value=1, max_value=100)
    offset = drf_serializers.IntegerField(default=0, min_value=0)
    client_search = drf_serializers.CharField(default='', allow_blank=True, max_length=128)
    client_type = drf_serializers.ChoiceField(choices=['', 'sdk', 'agent'], default='')
    state = drf_serializers.ChoiceField(choices=['', 'online', 'offline', 'inactive'], default='')


class CredentialClientSignatureAuthenticationMixin:
    max_clock_skew = 300
    replay_timeout = 660

    def fetch_user_data(self, key_id, algorithm=None):
        if algorithm != 'hmac-sha256':
            return None, None
        return super().fetch_user_data(key_id, algorithm)

    def validate_authenticated_request(self, request, user, key_id):
        try:
            request_time = parsedate_to_datetime(request.headers['Date'])
            if request_time.tzinfo is None:
                raise ValueError
        except (KeyError, OverflowError, TypeError, ValueError):
            raise AuthenticationFailed(
                _('The credential client request date is invalid.'), code='invalid_request_date',
            ) from None
        if abs((timezone.now() - request_time).total_seconds()) > self.max_clock_skew:
            raise AuthenticationFailed(
                _('The credential client request has expired.'), code='request_expired',
            )

        actual_digest = 'SHA-256=' + base64.b64encode(
            hashlib.sha256(request.body).digest()
        ).decode('ascii')
        if not hmac.compare_digest(request.headers.get('Digest', ''), actual_digest):
            raise AuthenticationFailed(
                _('The credential client request body is invalid.'), code='invalid_digest',
            )

        request_id = request.headers.get('X-JMS-Request-ID', '')
        try:
            request_id = str(uuid.UUID(request_id))
        except (TypeError, ValueError, AttributeError):
            raise AuthenticationFailed(
                _('The credential client request ID is invalid.'), code='invalid_request_id',
            ) from None
        try:
            is_new = cache.add(
                f'credential-client-request:{key_id}:{request_id}', True,
                timeout=self.replay_timeout,
            )
        except Exception as exc:
            raise AuthenticationFailed(
                _('Credential client replay protection is unavailable.'),
                code='replay_protection_unavailable',
            ) from exc
        if not is_new:
            raise AuthenticationFailed(
                _('The credential client request has already been used.'), code='request_replayed',
            )


class CredentialClientServiceAuthentication(
    CredentialClientSignatureAuthenticationMixin, ServiceAuthentication,
):
    required_headers = CREDENTIAL_CLIENT_SIGNATURE_HEADERS


class CredentialClientApplicationAgentAuthentication(CredentialClientServiceAuthentication):
    source = 'jms-pam-agent'



class CredentialClientAgentAuthentication(
    CredentialClientSignatureAuthenticationMixin, CredentialAgentAuthentication,
):
    required_headers = CREDENTIAL_CLIENT_SIGNATURE_HEADERS


class ApplicationCredentialViewSet(ApplicationAuditMixin, OrgBulkModelViewSet):
    model = ApplicationCredential
    serializer_class = serializers.ApplicationCredentialSerializer
    serializer_classes = {'list': serializers.ApplicationCredentialListSerializer}
    filterset_fields = ('id', 'name', 'key', 'mode', 'status', 'is_active', 'applications')
    search_fields = ('name', 'key', 'comment')
    ordering_fields = ('name', 'status', 'date_last_rotated', 'date_created')
    rbac_perms = {
        'start_cycle': 'accounts.change_applicationcredential',
        'prepare_rotation': 'accounts.change_applicationcredential',
        'check_preparation': 'accounts.change_applicationcredential',
        'start_rotation': 'accounts.change_applicationcredential',
        'check_usage': 'accounts.change_applicationcredential',
        'check_secret_change': 'accounts.change_applicationcredential',
        'change_secret': 'accounts.change_applicationcredential',
        'complete_rotation': 'accounts.change_applicationcredential',
        'cancel_rotation': 'accounts.change_applicationcredential',
        'rotation_status': 'accounts.view_applicationcredential',
        'rotation_events': 'accounts.view_applicationcredential',
        'event_history': 'accounts.view_applicationcredential',
        'event_cycles': 'accounts.view_applicationcredential',
        'access_applications': 'accounts.view_applicationcredential',
        'retry_change': ['accounts.change_applicationcredential', 'accounts.add_changesecretexecution'],
    }

    @transaction.atomic
    def perform_destroy(self, instance):
        if instance.status != ApplicationCredential.Status.idle:
            raise ValidationError(_('A rotating credential policy cannot be deleted.'))
        return super().perform_destroy(instance)

    @action(methods=['get'], detail=True, url_path='access-applications')
    def access_applications(self, request, *args, **kwargs):
        credential = self.get_object()
        scope = Q(credential_clients__isnull=False)
        online = scope & Q(
            is_active=True, credential_clients__is_active=True,
            credential_clients__date_last_seen__gte=timezone.now() - timezone.timedelta(minutes=2),
        )
        applications = credential.applications.annotate(
            instances_amount=Count('credential_clients', filter=scope, distinct=True),
            online_instances_amount=Count('credential_clients', filter=online, distinct=True),
            last_reported=Max('credential_clients__date_last_seen', filter=scope),
        ).order_by('name', 'id')
        results = [{
            'id': str(item.id), 'name': item.name, 'is_active': item.is_active,
            'instances_amount': item.instances_amount,
            'online_instances_amount': item.online_instances_amount,
            'last_reported': item.last_reported,
        } for item in applications]
        return Response({
            'applications_amount': len(results),
            'instances_amount': sum(item['instances_amount'] for item in results),
            'online_instances_amount': sum(item['online_instances_amount'] for item in results),
            'results': results,
        })

    @action(methods=['post'], detail=True, url_path='start-cycle')
    def start_cycle(self, request, *args, **kwargs):
        from accounts.credential_rotation.manual_cycles import start
        credential, cycle_id = start(self.get_object().id, request.user.name, request.user.id)
        return Response({
            'credential': self.get_serializer(credential).data,
            'cycle_id': str(cycle_id),
        }, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=True, url_path='prepare')
    def prepare_rotation(self, request, *args, **kwargs):
        credential = CredentialRotationManager(self.get_object().id).prepare(request.user.name, request.user.id)
        return Response(self.get_serializer(credential).data)

    @action(methods=['post'], detail=True, url_path='check-preparation')
    def check_preparation(self, request, *args, **kwargs):
        from accounts.credential_rotation.preparation import check
        credential = check(self.get_object().id)
        return Response(self.get_serializer(credential).data)

    @action(methods=['post'], detail=True, url_path='start')
    def start_rotation(self, request, *args, **kwargs):
        credential = self.get_object()
        if not request.user.has_perm('accounts.verify_account'):
            raise PermissionDenied()
        credential = CredentialRotationManager(credential.id).start(request.user.name, request.user.id)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='change-secret')
    def change_secret(self, request, *args, **kwargs):
        credential_id = self.get_object().id
        try:
            credential = CredentialRotationManager(credential_id).change_secret()
        except JMSException as exc:
            if exc.get_codes() != 'credential_rotation_clients_not_ready':
                raise
            from accounts.credential_rotation.participants import build
            credential = ApplicationCredential.objects.get(pk=credential_id)
            rotation_status = build(credential)
            return Response({
                'blockers': rotation_status['blockers'],
                'rotation_status': rotation_status,
            }, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='check-usage')
    def check_usage(self, request, *args, **kwargs):
        credential, blockers = CredentialRotationManager(self.get_object().id).check_usage()
        if blockers:
            from accounts.credential_rotation.participants import build
            return Response({
                'blockers': blockers,
                'rotation_status': build(credential),
            }, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['get'], detail=True, url_path='rotation-status')
    def rotation_status(self, request, *args, **kwargs):
        from accounts.credential_rotation.participants import build
        return Response(build(self.get_object()))

    @action(methods=['get'], detail=True, url_path='rotation-events')
    def rotation_events(self, request, *args, **kwargs):
        from accounts.credential_rotation.events import timeline
        query = CredentialEventQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        return Response(timeline(self.get_object(), query.validated_data.get('rotation_id')))

    @action(methods=['get'], detail=True, url_path='event-history')
    def event_history(self, request, *args, **kwargs):
        from accounts.credential_rotation.history import client_history, directory
        credential = self.get_object()
        query = CredentialEventQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        limit, offset = data['limit'], data['offset']
        if data.get('client_id'):
            return Response(client_history(credential, data['client_id'], limit, offset))
        clients = directory(credential, data['client_search'], data['client_type'], data['state'])
        return Response({'count': len(clients), 'results': clients[offset:offset + limit]})

    @action(methods=['get'], detail=True, url_path='event-cycles')
    def event_cycles(self, request, *args, **kwargs):
        from accounts.credential_rotation.cycles import cycle_detail, cycle_directory
        query = CredentialEventQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        data = query.validated_data
        credential = self.get_object()
        if data.get('cycle_id'):
            return Response(cycle_detail(credential, data['cycle_id']))
        return Response(cycle_directory(credential, data['limit'], data['offset']))

    @action(methods=['post'], detail=True, url_path='check-secret-change')
    def check_secret_change(self, request, *args, **kwargs):
        credential = CredentialRotationManager(self.get_object().id).check_secret_change()
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='complete')
    def complete_rotation(self, request, *args, **kwargs):
        credential, blockers = CredentialRotationManager(self.get_object().id).complete()
        if blockers:
            from accounts.credential_rotation.participants import build
            return Response({
                'blockers': blockers,
                'rotation_status': build(credential),
            }, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='cancel')
    def cancel_rotation(self, request, *args, **kwargs):
        params = serializers.CredentialRotationReasonSerializer(data=request.data)
        params.is_valid(raise_exception=True)
        credential = CredentialRotationManager(self.get_object().id).cancel(**params.validated_data)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='retry-change')
    def retry_change(self, request, *args, **kwargs):
        from accounts.credential_rotation.execution import execute
        credential = self.get_object()
        params = serializers.CredentialChangeRetrySerializer(data=request.data)
        params.is_valid(raise_exception=True)
        rotation = credential.rotation_records.first()
        if not rotation:
            raise JMSException(_('No active rotation.'))
        execute(rotation.id, request.user.name,
                previous_execution_id=params.validated_data['execution_id'],
                reason=params.validated_data['reason'])
        credential.refresh_from_db()
        serializer = self.get_serializer(credential)
        return Response(serializer.data)


class CredentialApplicationBindingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialApplicationBinding
    serializer_class = serializers.CredentialApplicationBindingSerializer
    filterset_fields = ('credential', 'application')
    search_fields = ('credential__name', 'credential__key', 'application__name')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'credential', 'application'
        ).annotate(clients_amount=Count('client_statuses', distinct=True))

    def perform_destroy(self, instance):
        if instance.credential.status != ApplicationCredential.Status.idle:
            raise ValidationError(_('An application cannot be unbound during rotation.'))
        return super().perform_destroy(instance)


class CredentialClientInstanceViewSet(
    ApplicationAuditMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialClientInstance
    serializer_class = serializers.CredentialClientInstanceSerializer
    filterset_fields = ('application', 'type', 'is_active')
    search_fields = ('instance_id', 'application__name')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('application').prefetch_related(
            'credential_statuses__binding__credential', 'credential_statuses__applied_account',
        )
        credential = self.request.query_params.get('credential')
        if credential:
            queryset = queryset.filter(application__credential_bindings__credential_id=credential).distinct()
        return queryset

    def perform_destroy(self, instance):
        if instance.online:
            raise ValidationError(_('An online client cannot be deleted.'))
        if instance.credential_statuses.exclude(
            binding__credential__status=ApplicationCredential.Status.idle,
        ).exists():
            raise ValidationError(_(
                'Disable the rotating client with a reason before deleting it.'
            ))
        return super().perform_destroy(instance)


class CredentialClientViewSet(ApplicationAuditMixin, JMSGenericViewSet):
    authentication_classes = [
        CredentialClientApplicationAgentAuthentication,
        CredentialClientServiceAuthentication,
    ]
    permission_classes = [IsCredentialClient]
    client_audit_events = {
        'credential': AuditEvent.CREDENTIAL_FETCHED,
        'confirm': AuditEvent.CREDENTIAL_CONFIRMED,
        'command_result': AuditEvent.COMMAND_RESULT,
    }
    serializer_classes = {
        'accounts': serializers.AuthorizedAccountsSerializer,
        'credential': serializers.CredentialFetchSerializer,
        'confirm': serializers.CredentialConfirmSerializer,
        'sync_agent': serializers.CredentialAgentSyncSerializer,
        'commands': serializers.ApplicationCommandPollSerializer,
        'command_result': serializers.ApplicationCommandResultSerializer,
    }

    class ClientUpgradeRequired(APIException):
        status_code = 426
        default_code = 'client_upgrade_required'
        default_detail = _('The client protocol or configuration format is not supported.')

    @staticmethod
    def _version(value, default=None):
        if value in (None, ''):
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            raise CredentialClientViewSet.ClientUpgradeRequired() from None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        protocol = self._version(request.headers.get('X-JMS-Protocol-Version'))
        schema = self._version(request.headers.get('X-JMS-Config-Schema-Version'))
        if protocol != 1:
            raise self.ClientUpgradeRequired()
        if (isinstance(request.user, CredentialClientInstance) or request.headers.get('X-Source') == 'jms-pam-agent') and schema != 1:
            raise self.ClientUpgradeRequired()

    def get_client_manager(self, data):
        manager = super().get_client_manager(data)
        manager.update_client_metadata(
            self.request.headers.get('X-JMS-Client-Version', ''),
            self._version(self.request.headers.get('X-JMS-Protocol-Version')),
            self._version(self.request.headers.get('X-JMS-Config-Schema-Version')),
        )
        if manager.client.type == CredentialClientInstance.Type.agent and manager.client.config_schema_version != 1:
            raise self.ClientUpgradeRequired()
        return manager

    @action(methods=['get'], detail=False, url_path='credential')
    def credential(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        response = Response(manager.fetch(
            data.get('key', ''), get_request_ip(request), data.get('account_id'),
        ))
        response['Cache-Control'] = 'no-store'
        return response

    @action(methods=['get'], detail=False, url_path='accounts')
    def accounts(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        response = Response(manager.authorized_accounts(
            limit=data.get('limit'), offset=data['offset'], search=data.get('search', ''),
        ))
        response['Cache-Control'] = 'no-store'
        return response

    @action(methods=['post'], detail=False)
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        return Response(manager.confirm(
            data['key'], data['revision'], data['account_id']
        ))

    @action(methods=['get'], detail=False, url_path='commands')
    def commands(self, request, *args, **kwargs):
        from accounts.credential_client.commands import pending
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        manager = self.get_client_manager(serializer.validated_data)
        response = Response({'commands': pending(manager.client)})
        response['Cache-Control'] = 'no-store'
        return response

    @action(methods=['post'], detail=False, url_path='command-result')
    def command_result(self, request, *args, **kwargs):
        from accounts.credential_client.commands import report
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        return Response(report(manager.client, data['command_id'], data['status'], data['error_code']))

    @action(methods=['post'], detail=False, url_path='agent/sync')
    def sync_agent(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        response = Response(manager.sync_agent(**{
            key: value for key, value in data.items() if key != 'instance_id'
        }))
        response['Cache-Control'] = 'no-store'
        return response
