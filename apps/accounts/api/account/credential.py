from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts import serializers
from accounts.credential_client import CredentialClientManager
from accounts.credential_client.manager import ClientAccessConfigurationManager
from accounts.credential_rotation import CredentialRotationManager
from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    ApplicationCredential, ClientAccessConfiguration, CredentialRotationRecord,
)
from accounts.permissions import IsCredentialClient
from authentication.backends.drf import (
    CredentialAgentAuthentication, ServiceAuthentication,
)
from common.api import JMSGenericViewSet
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from authentication.permissions import UserConfirmation, ConfirmType
from rbac.permissions import RBACPermission

__all__ = [
    'ApplicationCredentialViewSet', 'CredentialApplicationBindingViewSet',
    'CredentialClientInstanceViewSet', 'CredentialClientViewSet',
    'ClientAccessConfigurationViewSet', 'CredentialRotationRecordViewSet',
]


class ApplicationCredentialViewSet(OrgBulkModelViewSet):
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
    }

    def perform_destroy(self, instance):
        if instance.status != ApplicationCredential.Status.idle:
            raise ValidationError(_('A rotating application credential cannot be deleted.'))
        if instance.access_configurations.exists():
            raise ValidationError(_('Remove this credential from client access configurations before deleting it.'))
        return super().perform_destroy(instance)

    @action(methods=['post'], detail=True, url_path='start')
    def start_rotation(self, request, *args, **kwargs):
        credential = CredentialRotationManager(self.get_object().id).start(request.user.name)
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
        credential = CredentialRotationManager(self.get_object().id).cancel()
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
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialClientInstance
    serializer_class = serializers.CredentialClientInstanceSerializer
    filterset_fields = ('application', 'configuration', 'type', 'is_active')
    search_fields = ('instance_id', 'application__name')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('application', 'configuration').prefetch_related(
            'credential_statuses__binding__credential', 'credential_statuses__applied_account'
        )
        credential = self.request.query_params.get('credential')
        if credential:
            queryset = queryset.filter(credential_statuses__binding__credential=credential).distinct()
        return queryset

    def perform_destroy(self, instance):
        if instance.online:
            raise ValidationError(_('An online client cannot be deleted.'))
        return super().perform_destroy(instance)


class CredentialClientViewSet(JMSGenericViewSet):
    authentication_classes = [CredentialAgentAuthentication, ServiceAuthentication]
    permission_classes = [IsCredentialClient]
    serializer_classes = {
        'credential': serializers.CredentialFetchSerializer,
        'heartbeat': serializers.CredentialHeartbeatSerializer,
        'confirm': serializers.CredentialConfirmSerializer,
        'register_agent': serializers.CredentialAgentRegisterSerializer,
    }

    @action(methods=['get'], detail=False, url_path='credential')
    def credential(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = CredentialClientManager(
            request.user, data.get('configuration_id'), data.get('instance_id', '')
        )
        response = Response(manager.fetch(data['key'], get_request_ip(request)))
        response['Cache-Control'] = 'no-store'
        return response

    @action(methods=['post'], detail=False)
    def heartbeat(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = CredentialClientManager(
            request.user, data.get('configuration_id'), data.get('instance_id', '')
        )
        return Response(manager.heartbeat(data['credentials']))

    @action(methods=['post'], detail=False)
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = CredentialClientManager(
            request.user, data.get('configuration_id'), data.get('instance_id', '')
        )
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
        identity = CredentialClientManager.register_agent(
            data['token'], data['instance_id'], data.get('name', '')
        )
        return Response(identity, status=status.HTTP_201_CREATED)


class ClientAccessConfigurationViewSet(OrgBulkModelViewSet):
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
