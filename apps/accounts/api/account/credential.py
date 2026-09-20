import base64
import hashlib
import hmac
import uuid
from email.utils import parsedate_to_datetime

from django.core.cache import cache
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, AuthenticationFailed, ValidationError, PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts import serializers
from accounts.const import AuditEvent
from accounts.credential_client import CredentialClientManager
from accounts.credential_client.manager import ClientAccessConfigurationManager
from accounts.credential_rotation import CredentialRotationManager
from accounts.mixins import ApplicationAuditMixin
from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    ApplicationCredential, ClientAccessConfiguration, CredentialRotationRecord,
)
from accounts.permissions import IsCredentialClient
from authentication.backends.drf import (
    CredentialAgentAuthentication, ServiceAuthentication,
)
from common.api import JMSGenericViewSet
from common.exceptions import JMSException
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from authentication.permissions import UserConfirmation, ConfirmType
from rbac.permissions import RBACPermission

__all__ = [
    'ApplicationCredentialViewSet', 'CredentialApplicationBindingViewSet',
    'CredentialClientInstanceViewSet', 'CredentialClientViewSet',
    'ClientAccessConfigurationViewSet', 'CredentialRotationRecordViewSet',
]


CREDENTIAL_CLIENT_SIGNATURE_HEADERS = [
    '(request-target)', 'date', 'digest', 'x-jms-request-id', 'x-jms-client-version',
    'x-jms-protocol-version', 'x-jms-config-schema-version',
]


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


class CredentialClientAgentAuthentication(
    CredentialClientSignatureAuthenticationMixin, CredentialAgentAuthentication,
):
    required_headers = CREDENTIAL_CLIENT_SIGNATURE_HEADERS


class ApplicationCredentialViewSet(ApplicationAuditMixin, OrgBulkModelViewSet):
    model = ApplicationCredential
    serializer_class = serializers.ApplicationCredentialSerializer
    filterset_fields = ('id', 'name', 'key', 'type', 'rotation_mode', 'status', 'is_active', 'applications')
    search_fields = ('name', 'key', 'comment')
    ordering_fields = ('name', 'status', 'date_last_rotated', 'date_created')
    rbac_perms = {
        'start_rotation': 'accounts.change_applicationcredential',
        'check_usage': 'accounts.change_applicationcredential',
        'check_secret_change': 'accounts.change_applicationcredential',
        'change_secret': 'accounts.change_applicationcredential',
        'complete_rotation': 'accounts.change_applicationcredential',
        'cancel_rotation': 'accounts.change_applicationcredential',
        'retry_change': ['accounts.change_applicationcredential', 'accounts.add_changesecretexecution'],
    }

    def perform_destroy(self, instance):
        if instance.status != ApplicationCredential.Status.idle:
            raise ValidationError(_('A rotating application credential cannot be deleted.'))
        if instance.access_configurations.exists():
            raise ValidationError(_('Remove this credential from client access configurations before deleting it.'))
        return super().perform_destroy(instance)

    @action(methods=['post'], detail=True, url_path='start')
    def start_rotation(self, request, *args, **kwargs):
        credential = self.get_object()
        if credential.rotation_mode == 'dual' and not request.user.has_perm('accounts.verify_account'):
            raise PermissionDenied()
        credential = CredentialRotationManager(credential.id).start(request.user.name, request.user.id)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='change-secret')
    def change_secret(self, request, *args, **kwargs):
        credential = CredentialRotationManager(self.get_object().id).change_secret()
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='check-usage')
    def check_usage(self, request, *args, **kwargs):
        credential, blockers = CredentialRotationManager(self.get_object().id).check_usage()
        if blockers:
            return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='check-secret-change')
    def check_secret_change(self, request, *args, **kwargs):
        credential = CredentialRotationManager(self.get_object().id).check_secret_change()
        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='complete')
    def complete_rotation(self, request, *args, **kwargs):
        credential, blockers = CredentialRotationManager(self.get_object().id).complete()
        if blockers:
            return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)
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
        if instance.application.access_configurations.filter(credentials=instance.credential).exists():
            raise ValidationError(_('Remove the credential from client access configurations before unbinding it.'))
        return super().perform_destroy(instance)


class CredentialClientInstanceViewSet(
    ApplicationAuditMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialClientInstance
    serializer_class = serializers.CredentialClientInstanceSerializer
    filterset_fields = ('application', 'configuration', 'type', 'is_active')
    search_fields = ('instance_id', 'application__name')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('application', 'configuration').prefetch_related(
            'credential_statuses__binding__credential', 'credential_statuses__applied_account',
            'configuration__credentials',
        )
        credential = self.request.query_params.get('credential')
        if credential:
            queryset = queryset.filter(credential_statuses__binding__credential=credential).distinct()
        return queryset

    def perform_destroy(self, instance):
        if instance.online:
            raise ValidationError(_('An online client cannot be deleted.'))
        return super().perform_destroy(instance)


class CredentialClientViewSet(ApplicationAuditMixin, JMSGenericViewSet):
    authentication_classes = [
        CredentialClientAgentAuthentication, CredentialClientServiceAuthentication,
    ]
    permission_classes = [IsCredentialClient]
    client_audit_events = {
        'credential': AuditEvent.CREDENTIAL_FETCHED,
        'confirm': AuditEvent.CREDENTIAL_CONFIRMED,
    }
    serializer_classes = {
        'credential': serializers.CredentialFetchSerializer,
        'heartbeat': serializers.CredentialHeartbeatSerializer,
        'confirm': serializers.CredentialConfirmSerializer,
        'register_agent': serializers.CredentialAgentRegisterSerializer,
        'sync_agent': serializers.CredentialAgentSyncSerializer,
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
        if self.action == 'register_agent':
            return
        protocol = self._version(request.headers.get('X-JMS-Protocol-Version'))
        schema = self._version(request.headers.get('X-JMS-Config-Schema-Version'))
        if protocol != 1:
            raise self.ClientUpgradeRequired()
        if isinstance(request.user, CredentialClientInstance) and schema != 1:
            raise self.ClientUpgradeRequired()

    def get_client_manager(self, data):
        manager = super().get_client_manager(data)
        manager.update_client_metadata(
            self.request.headers.get('X-JMS-Client-Version', ''),
            self._version(self.request.headers.get('X-JMS-Protocol-Version')),
            self._version(self.request.headers.get('X-JMS-Config-Schema-Version')),
        )
        return manager

    @action(methods=['get'], detail=False, url_path='credential')
    def credential(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        response = Response(manager.fetch(data['key'], get_request_ip(request)))
        response['Cache-Control'] = 'no-store'
        return response

    @action(methods=['post'], detail=False)
    def heartbeat(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        return Response(manager.heartbeat(data['credentials']))

    @action(methods=['post'], detail=False)
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        return Response(manager.confirm(
            data['key'], data['revision'], data['account_id']
        ))

    @action(
        methods=['post'], detail=False, url_path='register-agent',
        authentication_classes=[], permission_classes=[AllowAny],
    )
    def register_agent(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data['protocol_version'] != 1 or data['config_schema_version'] != 1:
            raise self.ClientUpgradeRequired()
        identity = CredentialClientManager.register_agent(
            data['token'], data['instance_id'], data.get('name', ''),
            data['client_version'], data['protocol_version'], data['config_schema_version'],
        )
        return Response(identity, status=status.HTTP_201_CREATED)

    @action(methods=['post'], detail=False, url_path='agent/sync')
    def sync_agent(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = self.get_client_manager(data)
        response = Response(manager.sync_agent(**data))
        response['Cache-Control'] = 'no-store'
        return response


class ClientAccessConfigurationViewSet(ApplicationAuditMixin, OrgBulkModelViewSet):
    model = ClientAccessConfiguration
    serializer_class = serializers.ClientAccessConfigurationSerializer
    filterset_fields = ('application', 'type', 'is_active', 'credentials')
    search_fields = ('name', 'comment')
    ordering_fields = ('name', 'type', 'date_created')
    rbac_perms = {
        'materials': ['accounts.change_clientaccessconfiguration', 'accounts.change_integrationapplication'],
    }

    def perform_destroy(self, instance):
        if instance.credentials.exclude(status='idle').exists():
            raise ValidationError(_('Disable the client configuration instead of deleting it during rotation.'))
        return super().perform_destroy(instance)

    @action(
        methods=['post'], detail=True, url_path='materials',
        permission_classes=[RBACPermission, UserConfirmation.require(ConfirmType.MFA)],
    )
    def materials(self, request, *args, **kwargs):
        instance = self.get_object()
        endpoint = request.build_absolute_uri('/').rstrip('/')
        data = ClientAccessConfigurationManager(instance).materials(endpoint)
        response = Response(data)
        response['Cache-Control'] = 'no-store'
        return response


class CredentialRotationRecordViewSet(mixins.ListModelMixin, OrgGenericViewSet):
    model = CredentialRotationRecord
    serializer_class = serializers.CredentialRotationRecordSerializer
    filterset_fields = ('credential', 'status')
    search_fields = ('created_by', 'comment')
    rbac_perms = {'list': 'accounts.view_applicationcredential'}
