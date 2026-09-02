from django.core import signing
from django.core.cache import cache
from django.db import transaction
from django.db.models import Count, F
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from accounts import serializers
from accounts.const import ChangeSecretRecordStatusChoice
from accounts.models import (
    ChangeSecretRecord, CredentialApplicationBinding,
    CredentialClientInstance, CredentialClientStatus, CredentialPolicy,
    IntegrationApplication,
)
from accounts.permissions import IsCredentialClient
from audits.models import IntegrationApplicationLog
from authentication.backends.drf import (
    CredentialAgentAuthentication, ServiceAuthentication,
)
from common.utils import get_request_ip, random_string
from orgs.mixins.api import OrgBulkModelViewSet, OrgGenericViewSet
from orgs.utils import tmp_to_org

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

    @staticmethod
    def _get_locked(pk):
        return CredentialPolicy.objects.select_for_update().select_related(
            'primary_account', 'backup_account', 'published_account'
        ).get(pk=pk)

    def perform_destroy(self, instance):
        if instance.status != CredentialPolicy.Status.idle:
            raise ValidationError(_('A rotating credential policy cannot be deleted.'))
        return super().perform_destroy(instance)

    @action(methods=['post'], detail=True, url_path='start')
    def start_rotation(self, request, *args, **kwargs):
        with transaction.atomic():
            policy = self._get_locked(kwargs['pk'])
            if policy.status != CredentialPolicy.Status.idle:
                raise ValidationError(_('The credential policy is already rotating.'))

            states = list(
                CredentialClientStatus.objects.select_for_update().filter(
                    binding__policy=policy,
                    client__is_active=True,
                    client__type=F('binding__application__credential_access_mode'),
                )
            )
            if not states:
                raise ValidationError(_('No active application client uses this credential policy.'))

            policy.revision += 1
            policy.published_account = policy.backup_account
            policy.primary_version_at_start = policy.primary_account.version
            policy.status = CredentialPolicy.Status.waiting_backup
            policy.rotation_cancelled = False
            policy.date_rotation_started = timezone.now()
            policy.save(update_fields=[
                'revision', 'published_account', 'primary_version_at_start',
                'status', 'rotation_cancelled', 'date_rotation_started',
                'date_updated',
            ])
            CredentialClientStatus.objects.filter(id__in=[state.id for state in states]).update(
                required_revision=policy.revision,
                is_rotation_participant=True,
            )
        return Response(self.get_serializer(policy).data)

    @action(methods=['post'], detail=True, url_path='check-usage')
    def check_usage(self, request, *args, **kwargs):
        with transaction.atomic():
            policy = self._get_locked(kwargs['pk'])
            if policy.status != CredentialPolicy.Status.waiting_backup:
                raise ValidationError(_('The credential policy is not waiting for the backup account.'))
            blockers = policy.get_blockers()
            if blockers:
                return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)
            policy.status = CredentialPolicy.Status.ready_for_change
            policy.save(update_fields=['status', 'date_updated'])
        return Response(self.get_serializer(policy).data)

    @action(methods=['post'], detail=True, url_path='check-secret-change')
    def check_secret_change(self, request, *args, **kwargs):
        with transaction.atomic():
            policy = self._get_locked(kwargs['pk'])
            if policy.status != CredentialPolicy.Status.ready_for_change:
                raise ValidationError(_('The credential policy is not ready for secret change.'))

            primary = policy.primary_account
            primary.refresh_from_db()
            record = ChangeSecretRecord.objects.filter(
                account=primary,
                account_version=policy.primary_version_at_start,
                status=ChangeSecretRecordStatusChoice.success,
                date_finished__gte=policy.date_rotation_started,
            ).order_by('-date_finished').first()
            changed = (
                primary.version > policy.primary_version_at_start
                and primary.change_secret_status == ChangeSecretRecordStatusChoice.success
                and record is not None
            )
            if not changed:
                raise ValidationError(_('The primary account secret has not been changed and verified successfully.'))

            policy.revision += 1
            policy.published_account = primary
            policy.status = CredentialPolicy.Status.waiting_primary
            policy.save(update_fields=[
                'revision', 'published_account', 'status', 'date_updated',
            ])
            CredentialClientStatus.objects.filter(
                binding__policy=policy, is_rotation_participant=True
            ).update(required_revision=policy.revision)
        return Response(self.get_serializer(policy).data)

    @action(methods=['post'], detail=True, url_path='complete')
    def complete_rotation(self, request, *args, **kwargs):
        with transaction.atomic():
            policy = self._get_locked(kwargs['pk'])
            if policy.status != CredentialPolicy.Status.waiting_primary:
                raise ValidationError(_('The credential policy is not waiting for the primary account.'))
            blockers = policy.get_blockers()
            if blockers:
                return Response({'blockers': blockers}, status=status.HTTP_409_CONFLICT)

            if not policy.rotation_cancelled:
                policy.date_last_rotated = timezone.now()
            policy.status = CredentialPolicy.Status.idle
            policy.primary_version_at_start = None
            policy.date_rotation_started = None
            policy.rotation_cancelled = False
            policy.save(update_fields=[
                'status', 'date_last_rotated', 'primary_version_at_start',
                'date_rotation_started', 'rotation_cancelled', 'date_updated',
            ])
            CredentialClientStatus.objects.filter(
                binding__policy=policy, is_rotation_participant=True
            ).update(required_revision=None, is_rotation_participant=False)
        return Response(self.get_serializer(policy).data)

    @action(methods=['post'], detail=True, url_path='cancel')
    def cancel_rotation(self, request, *args, **kwargs):
        with transaction.atomic():
            policy = self._get_locked(kwargs['pk'])
            if policy.status not in (
                CredentialPolicy.Status.waiting_backup,
                CredentialPolicy.Status.ready_for_change,
            ):
                raise ValidationError(_('This credential rotation cannot be cancelled.'))
            policy.revision += 1
            policy.published_account = policy.primary_account
            policy.status = CredentialPolicy.Status.waiting_primary
            policy.rotation_cancelled = True
            policy.save(update_fields=[
                'revision', 'published_account', 'status',
                'rotation_cancelled', 'date_updated',
            ])
            CredentialClientStatus.objects.filter(
                binding__policy=policy, is_rotation_participant=True
            ).update(required_revision=policy.revision)
        return Response(self.get_serializer(policy).data)


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


class CredentialClientViewSet(viewsets.GenericViewSet):
    authentication_classes = [CredentialAgentAuthentication, ServiceAuthentication]
    permission_classes = [IsCredentialClient]
    serializer_classes = {
        'credential': serializers.CredentialFetchSerializer,
        'heartbeat': serializers.CredentialHeartbeatSerializer,
        'confirm': serializers.CredentialConfirmSerializer,
        'register_agent': serializers.CredentialAgentRegisterSerializer,
    }

    def get_serializer_class(self):
        return self.serializer_classes[self.action]

    @staticmethod
    def _get_application_and_client(request, instance_id=''):
        user = request.user
        if isinstance(user, CredentialClientInstance):
            if user.application.credential_access_mode != IntegrationApplication.AccessMode.agent:
                raise PermissionDenied(_('The application does not use Agent access mode.'))
            return user.application, user

        if user.credential_access_mode != IntegrationApplication.AccessMode.sdk:
            raise PermissionDenied(_('The application does not use SDK access mode.'))
        if not instance_id:
            raise ValidationError({'instance_id': _('This field is required for SDK access.')})
        client, created = CredentialClientInstance.objects.get_or_create(
            application=user,
            instance_id=instance_id,
            defaults={'type': CredentialClientInstance.Type.sdk},
        )
        if client.type != CredentialClientInstance.Type.sdk or not client.is_active:
            raise PermissionDenied(_('The SDK client instance is disabled.'))
        return user, client

    @staticmethod
    def _check_policy_access(application, policy):
        account_ids = {policy.primary_account_id, policy.backup_account_id}
        allowed = set(
            application.get_accounts().filter(id__in=account_ids).values_list('id', flat=True)
        )
        if allowed != account_ids:
            raise PermissionDenied(_('The application is not authorized for both policy accounts.'))

    @action(methods=['get'], detail=False, url_path='credential')
    def credential(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        application, client = self._get_application_and_client(
            request, serializer.validated_data.get('instance_id', '')
        )
        policy = CredentialPolicy.objects.select_related(
            'primary_account__asset__platform', 'backup_account', 'published_account'
        ).filter(key=serializer.validated_data['key'], is_active=True).first()
        if not policy:
            raise ValidationError({'key': _('Credential policy not found.')})
        self._check_policy_access(application, policy)

        now = timezone.now()
        with transaction.atomic():
            binding = CredentialApplicationBinding.objects.get_or_create(
                policy=policy, application=application
            )[0]
            state = CredentialClientStatus.objects.get_or_create(
                binding=binding, client=client
            )[0]
            state.fetched_revision = policy.revision
            state.date_fetched = now
            state.date_last_seen = now
            state.save(update_fields=[
                'fetched_revision', 'date_fetched', 'date_last_seen', 'date_updated',
            ])
            CredentialClientInstance.objects.filter(id=client.id).update(date_last_seen=now)

        account = policy.published_account
        asset = account.asset
        IntegrationApplicationLog.objects.create(
            remote_addr=get_request_ip(request),
            service=application.name,
            service_id=application.id,
            account=f'{account.name}({account.username})',
            asset=f'{asset.name}({asset.address})',
        )
        return Response({
            'key': policy.key,
            'revision': policy.revision,
            'asset': {
                'id': str(asset.id),
                'name': asset.name,
                'address': asset.address,
                'platform': {
                    'id': str(asset.platform_id),
                    'name': asset.platform.name,
                    'category': asset.platform.category,
                    'type': asset.platform.type,
                },
            },
            'account': {
                'id': str(account.id),
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.secret,
            },
        })

    @action(methods=['post'], detail=False)
    def heartbeat(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application, client = self._get_application_and_client(
            request, serializer.validated_data.get('instance_id', '')
        )
        now = timezone.now()
        updated = []
        for item in serializer.validated_data['credentials']:
            state = CredentialClientStatus.objects.select_related(
                'binding__policy'
            ).filter(
                binding__application=application,
                binding__policy__key=item['key'],
                client=client,
            ).first()
            if not state:
                continue
            policy = state.binding.policy
            if item['account_id'] not in (
                policy.primary_account_id, policy.backup_account_id
            ):
                continue
            state.applied_revision = item['revision']
            state.applied_account_id = item['account_id']
            state.date_last_seen = now
            state.date_applied = now
            state.save(update_fields=[
                'applied_revision', 'applied_account', 'date_applied',
                'date_last_seen', 'date_updated',
            ])
            updated.append(policy.key)
        CredentialClientInstance.objects.filter(id=client.id).update(date_last_seen=now)
        return Response({'updated': updated, 'date_last_seen': now})

    @action(methods=['post'], detail=False)
    def confirm(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application, client = self._get_application_and_client(
            request, serializer.validated_data.get('instance_id', '')
        )
        state = CredentialClientStatus.objects.select_related(
            'binding__policy'
        ).filter(
            binding__application=application,
            binding__policy__key=serializer.validated_data['key'],
            client=client,
        ).first()
        if not state:
            raise ValidationError(_('Fetch the credential before confirming it.'))
        policy = state.binding.policy
        if (
            serializer.validated_data['revision'] != policy.revision
            or serializer.validated_data['account_id'] != policy.published_account_id
        ):
            raise ValidationError(_('The credential revision is no longer current.'))
        now = timezone.now()
        state.applied_revision = policy.revision
        state.applied_account = policy.published_account
        state.date_applied = now
        state.date_last_seen = now
        state.save(update_fields=[
            'applied_revision', 'applied_account', 'date_applied',
            'date_last_seen', 'date_updated',
        ])
        CredentialClientInstance.objects.filter(id=client.id).update(date_last_seen=now)
        return Response({'key': policy.key, 'revision': policy.revision})

    @action(
        methods=['post'], detail=False, url_path='register-agent',
        authentication_classes=[], permission_classes=[AllowAny],
    )
    def register_agent(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']
        try:
            payload = signing.loads(token, salt='credential-agent-register', max_age=600)
        except signing.BadSignature as exc:
            raise ValidationError({'token': _('Invalid or expired registration token.')}) from exc

        used_key = f"credential-agent-register-used:{payload['nonce']}"
        with tmp_to_org(payload['org_id']):
            application = IntegrationApplication.objects.filter(
                id=payload['application_id'], is_active=True,
                credential_access_mode=IntegrationApplication.AccessMode.agent,
            ).first()
            if not application:
                raise ValidationError({'token': _('Integration application not found.')})
            if not cache.add(used_key, True, timeout=600):
                raise ValidationError({'token': _('Registration token has already been used.')})

            secret = random_string(48)
            client = CredentialClientInstance.objects.update_or_create(
                application=application,
                instance_id=serializer.validated_data['instance_id'],
                defaults={
                    'type': CredentialClientInstance.Type.agent,
                    'secret': secret,
                    'is_active': True,
                    'comment': serializer.validated_data.get('name', ''),
                },
            )[0]
        return Response({
            'agent_id': str(client.id),
            'agent_secret': secret,
            'application_id': str(application.id),
            'org_id': application.org_id,
        }, status=status.HTTP_201_CREATED)
