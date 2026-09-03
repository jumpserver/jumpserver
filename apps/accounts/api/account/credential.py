from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts import serializers
from accounts.credential_client import CredentialClientManager
from accounts.credential_rotation import CredentialRotationManager
from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    CredentialPolicy,
)
from accounts.permissions import IsCredentialClient
from authentication.backends.drf import (
    CredentialAgentAuthentication, ServiceAuthentication,
)
from common.api import JMSGenericViewSet
from common.utils import get_request_ip
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet

__all__ = [
    'CredentialPolicyViewSet', 'CredentialApplicationBindingViewSet',
    'CredentialClientInstanceViewSet', 'CredentialClientViewSet',
]


class CredentialPolicyViewSet(OrgBulkModelViewSet):
    model = CredentialPolicy
    serializer_class = serializers.CredentialPolicySerializer
    filterset_fields = ('id', 'name', 'key', 'status', 'is_active')
    search_fields = ('name', 'key', 'comment')
    ordering_fields = ('name', 'status', 'date_last_rotated', 'date_created')
    rbac_perms = {
        'start_rotation': 'accounts.change_credentialpolicy',
        'check_usage': 'accounts.change_credentialpolicy',
        'check_secret_change': 'accounts.change_credentialpolicy',
        'complete_rotation': 'accounts.change_credentialpolicy',
        'cancel_rotation': 'accounts.change_credentialpolicy',
    }

    def get_queryset(self):
        return super().get_queryset().select_related(
            'primary_account__asset__platform', 'backup_account', 'published_account'
        ).annotate(
            applications_amount=Count('application_bindings', distinct=True)
        )

    def perform_destroy(self, instance):
        if instance.status != CredentialPolicy.Status.idle:
            raise ValidationError(_('A rotating credential policy cannot be deleted.'))
        return super().perform_destroy(instance)

    @action(methods=['post'], detail=True, url_path='start')
    def start_rotation(self, request, *args, **kwargs):
        policy = CredentialRotationManager(kwargs['pk']).start()
        serializer = self.get_serializer(policy)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='check-usage')
    def check_usage(self, request, *args, **kwargs):
        policy, blockers = CredentialRotationManager(kwargs['pk']).check_usage()
        if blockers:
            return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(policy)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='check-secret-change')
    def check_secret_change(self, request, *args, **kwargs):
        policy = CredentialRotationManager(kwargs['pk']).check_secret_change()
        serializer = self.get_serializer(policy)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='complete')
    def complete_rotation(self, request, *args, **kwargs):
        policy, blockers = CredentialRotationManager(kwargs['pk']).complete()
        if blockers:
            return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)
        serializer = self.get_serializer(policy)
        return Response(serializer.data)

    @action(methods=['post'], detail=True, url_path='cancel')
    def cancel_rotation(self, request, *args, **kwargs):
        policy = CredentialRotationManager(kwargs['pk']).cancel()
        serializer = self.get_serializer(policy)
        return Response(serializer.data)


class CredentialApplicationBindingViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialApplicationBinding
    serializer_class = serializers.CredentialApplicationBindingSerializer
    filterset_fields = ('policy', 'application')
    search_fields = ('policy__name', 'policy__key', 'application__name')

    def get_queryset(self):
        return super().get_queryset().select_related(
            'policy', 'application'
        ).annotate(clients_amount=Count('client_statuses', distinct=True))

    def perform_destroy(self, instance):
        if instance.policy.status != CredentialPolicy.Status.idle:
            raise ValidationError(_('An application cannot be unbound during rotation.'))
        return super().perform_destroy(instance)


class CredentialClientInstanceViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, mixins.DestroyModelMixin, OrgGenericViewSet,
):
    model = CredentialClientInstance
    serializer_class = serializers.CredentialClientInstanceSerializer
    filterset_fields = ('application', 'type', 'is_active')
    search_fields = ('instance_id', 'application__name')

    def get_queryset(self):
        queryset = super().get_queryset().select_related('application').prefetch_related(
            'credential_statuses__binding__policy', 'credential_statuses__applied_account'
        )
        policy = self.request.query_params.get('policy')
        if policy:
            queryset = queryset.filter(credential_statuses__binding__policy=policy).distinct()
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
            request.user, data.get('instance_id', '')
        )
        return Response(manager.fetch(data['key'], get_request_ip(request)))

    @action(methods=['post'], detail=False)
    def heartbeat(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = CredentialClientManager(
            request.user, data.get('instance_id', '')
        )
        return Response(manager.heartbeat(data['credentials']))

    @action(methods=['post'], detail=False)
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        manager = CredentialClientManager(
            request.user, data.get('instance_id', '')
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
