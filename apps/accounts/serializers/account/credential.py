import re

from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import (
    Account, CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, ApplicationCredential, IntegrationApplication,
    ClientAccessConfiguration,
)
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = [
    'ApplicationCredentialSerializer', 'CredentialApplicationBindingSerializer',
    'CredentialClientInstanceSerializer', 'CredentialClientStatusSerializer',
    'CredentialFetchSerializer',
    'CredentialConfirmSerializer', 'CredentialAgentRegisterSerializer',
    'CredentialAgentSyncSerializer',
    'ClientAccessConfigurationSerializer',
    'CredentialChangeRetrySerializer', 'CredentialRotationReasonSerializer',
]


SYSTEMD_UNIT = re.compile(r'^[A-Za-z0-9_.@:-]+\.service$')


class CredentialRotationReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=512, required=False, default='', allow_blank=True)


class CredentialChangeRetrySerializer(CredentialRotationReasonSerializer):
    execution_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=512, allow_blank=False)


class ApplicationCredentialSerializer(BulkOrgResourceModelSerializer):
    rotation = serializers.SerializerMethodField()
    precheck = serializers.SerializerMethodField()

    @staticmethod
    def get_precheck(instance):
        from accounts.credential_rotation.preflight import info
        return info(instance) if instance.mode == ApplicationCredential.Mode.alternating_rotation else None

    @staticmethod
    def get_rotation(instance):
        from accounts.credential_rotation.execution import execution_info
        return execution_info(instance)

    account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username', 'secret_type'),
        label=_('Account'), required=False, allow_null=True
    )
    alternate_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username'),
        label=_('Alternate account'), required=False, allow_null=True
    )
    active_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
        label=_('Active account')
    )
    asset = serializers.SerializerMethodField(label=_('Asset'))
    applications_amount = serializers.IntegerField(read_only=True)
    blockers = serializers.SerializerMethodField(label=_('Blockers'))
    applications = ObjectRelatedField(
        queryset=IntegrationApplication.objects, many=True, required=True,
        attrs=('id', 'name'), label=_('Integration applications')
    )
    last_fetched = serializers.DateTimeField(read_only=True)
    change_execution = ObjectRelatedField(read_only=True, attrs=('id', 'status', 'date_finished'))

    class Meta:
        model = ApplicationCredential
        fields_mini = ['id', 'name', 'key']
        fields_small = fields_mini + [
            'mode', 'asset', 'account', 'alternate_account',
            'active_account', 'revision', 'status', 'is_active',
            'last_fetched', 'date_last_rotated', 'applications_amount',
        ]
        fields = fields_small + [
            'applications', 'change_execution', 'rotation', 'precheck', 'blockers',
            'rotation_cancelled', 'date_rotation_started',
            'date_created', 'date_updated', 'created_by', 'comment',
        ]
        read_only_fields = [
            'key', 'active_account', 'revision', 'status',
            'applications_amount', 'blockers',
            'rotation_cancelled', 'date_rotation_started', 'date_last_rotated',
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related(
            'account__asset__platform', 'alternate_account', 'active_account', 'change_execution'
        ).prefetch_related('applications').annotate(
            applications_amount=Count('applications', distinct=True),
            last_fetched=Max('application_bindings__client_statuses__date_fetched'),
        )

    @staticmethod
    def get_asset(instance):
        asset = instance.asset
        if not asset:
            return None
        return {
            'id': str(asset.id),
            'name': asset.name,
            'address': asset.address,
            'platform': {
                'id': str(asset.platform_id),
                'name': asset.platform.name,
                'category': asset.platform.category,
                'type': asset.platform.type,
            },
        }

    @staticmethod
    def get_blockers(instance):
        if instance.status == ApplicationCredential.Status.idle:
            return []
        return instance.get_blockers()

    def validate(self, attrs):
        from accounts.credential_rotation.preflight import check_ownership
        attrs = self.validate_accounts(attrs)
        accounts = [
            attrs.get('account', getattr(self.instance, 'account', None)),
            attrs.get('alternate_account', getattr(self.instance, 'alternate_account', None)),
        ]
        mode = attrs.get('mode') or getattr(
            self.instance, 'mode', ApplicationCredential.Mode.subscription
        )
        if mode == ApplicationCredential.Mode.alternating_rotation:
            check_ownership(self.instance or ApplicationCredential(), accounts)
        applications = attrs.get('applications')
        if applications is None and self.instance:
            applications = list(self.instance.applications.all())
        if not applications:
            raise serializers.ValidationError({'applications': _('Select at least one application.')})
        if mode == ApplicationCredential.Mode.alternating_rotation:
            required = {item.id for item in accounts if item}
            unauthorized = [
                application.name for application in applications
                if not required.issubset(set(application.get_accounts().values_list('id', flat=True)))
            ]
            if unauthorized:
                raise serializers.ValidationError({'applications': _(
                    'These applications are not authorized for every credential account: {names}'
                ).format(names=', '.join(unauthorized))})
        if self.instance and 'applications' in attrs:
            removed = set(self.instance.applications.values_list('id', flat=True)) - {
                application.id for application in applications
            }
            in_use = self.instance.access_configurations.filter(application_id__in=removed).exists()
            if in_use:
                raise serializers.ValidationError({'applications': _(
                    'Remove this credential from the application access configuration first.'
                )})
        return attrs

    def validate_accounts(self, attrs):
        if self.instance and self.instance.status != ApplicationCredential.Status.idle:
            for field in ('account', 'alternate_account', 'is_active'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(_('Credential settings cannot be changed during rotation.'))
            if 'applications' in attrs and {
                item.id for item in attrs['applications']
            } != set(self.instance.applications.values_list('id', flat=True)):
                raise serializers.ValidationError(_('Credential settings cannot be changed during rotation.'))
        if self.instance and 'mode' in attrs and attrs['mode'] != self.instance.mode:
            raise serializers.ValidationError({'mode': _('The credential policy mode cannot be changed.')})
        account = attrs.get('account') or getattr(self.instance, 'account', None)
        mode = attrs.get('mode') or getattr(self.instance, 'mode', ApplicationCredential.Mode.subscription)
        alternate = attrs.get('alternate_account', getattr(self.instance, 'alternate_account', None))
        if mode == ApplicationCredential.Mode.subscription:
            attrs['account'] = None
            attrs['alternate_account'] = None
            attrs['active_account'] = None
            return attrs
        if not account:
            raise serializers.ValidationError({'account': _(
                'This field is required for alternating dual-account rotation.'
            )})
        if not alternate:
            raise serializers.ValidationError({'alternate_account': _(
                'This field is required for alternating dual-account rotation.'
            )})
        if not account:
            return attrs
        if account.id == alternate.id:
            raise serializers.ValidationError(_('The initial and alternate accounts must be different.'))
        if account.asset_id != alternate.asset_id:
            raise serializers.ValidationError(_('The initial and alternate accounts must belong to the same asset.'))
        if account.org_id != alternate.org_id:
            raise serializers.ValidationError(_('The initial and alternate accounts must belong to the same organization.'))
        if account.secret_type != alternate.secret_type:
            raise serializers.ValidationError(_('The initial and alternate accounts must use the same secret type.'))
        return attrs

    @staticmethod
    def sync_applications(instance, applications):
        from accounts.const import ApplicationEvent, AuditEvent
        from accounts.credential_client.audit import record
        from accounts.credential_client.events import enqueue

        wanted = {application.id: application for application in applications}
        removed = list(instance.application_bindings.exclude(
            application_id__in=wanted
        ).select_related('application'))
        instance.application_bindings.filter(id__in=[item.id for item in removed]).delete()
        existing = set(instance.application_bindings.values_list('application_id', flat=True))
        added = [
            CredentialApplicationBinding(
                credential=instance, application=application, org_id=instance.org_id,
            )
            for application_id, application in wanted.items() if application_id not in existing
        ]
        CredentialApplicationBinding.objects.bulk_create(added)
        for binding in removed:
            event = record(
                AuditEvent.AUTHORIZATION_REVOKED, credential=instance,
                application=binding.application,
            )
            enqueue(event, ApplicationEvent.CREDENTIAL_REVOKED)
        for binding in added:
            event = record(
                AuditEvent.AUTHORIZATION_GRANTED, credential=instance,
                application=binding.application,
            )
            enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)

    def create(self, validated_data):
        from accounts.credential_rotation.preflight import check_ownership
        applications = validated_data.pop('applications')
        accounts = [validated_data.get('account'), validated_data.get('alternate_account')]
        # Lock shared accounts before inserting a new credential, then recheck ownership.
        with transaction.atomic():
            list(Account.objects.select_for_update().filter(
                pk__in=[a.pk for a in accounts if a],
            ).order_by('id'))
            if validated_data.get('mode', ApplicationCredential.Mode.subscription) == ApplicationCredential.Mode.alternating_rotation:
                check_ownership(ApplicationCredential(), accounts)
                validated_data['active_account'] = validated_data['account']
            instance = super().create(validated_data)
            self.sync_applications(instance, applications)
            return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        from accounts.credential_rotation.preflight import check_ownership
        instance = ApplicationCredential.objects.select_for_update().get(pk=instance.pk)
        # Recheck stage constraints against the locked, current credential.
        self.instance = instance
        validated_data = self.validate(validated_data)
        applications = validated_data.pop('applications', None)
        account = validated_data.get('account', instance.account)
        accounts = [account, validated_data.get('alternate_account', instance.alternate_account)]
        # Existing bindings already exclude competing claims. Lock only newly
        # acquired accounts, avoiding lock inversion with subscription publication.
        existing_ids = {instance.account_id, instance.alternate_account_id}
        list(Account.objects.select_for_update().filter(
            pk__in=[a.pk for a in accounts if a and a.pk not in existing_ids],
        ).order_by('id'))
        if instance.mode == ApplicationCredential.Mode.alternating_rotation:
            check_ownership(instance, accounts)
        if account and instance.active_account_id not in {item.id for item in accounts if item}:
            validated_data['active_account'] = account
            validated_data['revision'] = instance.revision + 1
        instance = super().update(instance, validated_data)
        if applications is not None:
            self.sync_applications(instance, applications)
        return instance


class CredentialClientStatusSerializer(serializers.ModelSerializer):
    credential = serializers.SerializerMethodField(label=_('Credential policy'))
    applied_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'), label=_('Applied account')
    )

    class Meta:
        model = CredentialClientStatus
        fields = [
            'id', 'credential', 'fetched_revision', 'delivered_revision', 'applied_revision',
            'applied_account', 'required_revision', 'is_rotation_participant',
            'date_last_seen', 'date_fetched', 'date_delivered', 'date_applied',
        ]
        read_only_fields = fields

    @staticmethod
    def get_credential(instance):
        credential = instance.binding.credential
        return {
            'id': str(credential.id), 'name': credential.name,
            'key': credential.key, 'status': credential.status,
        }


class CredentialClientInstanceSerializer(BulkOrgResourceModelSerializer):
    configuration = ObjectRelatedField(read_only=True, attrs=('id', 'name'))
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'), label=_('Integration application')
    )
    online = serializers.SerializerMethodField(label=_('Online'))
    credential_statuses = CredentialClientStatusSerializer(many=True, read_only=True)
    configuration_current = serializers.SerializerMethodField()
    upgrade_required = serializers.SerializerMethodField()
    reason = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=512,
    )

    class Meta:
        model = CredentialClientInstance
        fields_mini = ['id', 'instance_id', 'type']
        fields_small = fields_mini + [
            'application', 'configuration', 'online', 'date_last_seen', 'is_active',
        ]
        fields = fields_small + [
            'client_version', 'protocol_version', 'config_schema_version',
            'config_digest', 'configuration_current', 'upgrade_required',
            'sync_status', 'sync_error', 'date_last_synced',
            'credential_statuses', 'reason', 'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = [
            'id', 'instance_id', 'type', 'application', 'online',
            'client_version', 'protocol_version', 'config_schema_version',
            'config_digest', 'configuration_current', 'upgrade_required',
            'sync_status', 'sync_error', 'date_last_synced',
            'date_last_seen', 'credential_statuses', 'date_created', 'date_updated',
        ]

    @staticmethod
    def get_online(instance):
        return instance.online

    @staticmethod
    def get_configuration_current(instance):
        if instance.type != CredentialClientInstance.Type.agent or not instance.config_digest:
            return None
        from accounts.credential_client.manager import CredentialClientManager
        return instance.config_digest == CredentialClientManager.agent_configuration_digest(
            instance.configuration
        )

    @staticmethod
    def get_upgrade_required(instance):
        return instance.protocol_version != 1 or (
            instance.type == CredentialClientInstance.Type.agent
            and instance.config_schema_version != 1
        )

    def validate(self, attrs):
        if (
            self.instance and self.instance.is_active
            and attrs.get('is_active') is False
            and self.instance.credential_statuses.exclude(
                binding__credential__status=ApplicationCredential.Status.idle,
            ).exists()
            and not attrs.get('reason', '').strip()
        ):
            raise serializers.ValidationError({
                'reason': _('Explain why the rotating client should be excluded.')
            })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        reason = validated_data.pop('reason', '').strip()
        if instance.is_active and validated_data.get('is_active') is False:
            from accounts.credential_rotation.participants import exclude

            credential_ids = list(instance.credential_statuses.exclude(
                binding__credential__status=ApplicationCredential.Status.idle,
            ).values_list('binding__credential_id', flat=True))
            locked_credentials = ApplicationCredential.objects.select_for_update().filter(
                id__in=credential_ids,
            ).order_by('id')
            credentials = {credential.id: credential for credential in locked_credentials}
            states = list(CredentialClientStatus.objects.select_for_update().select_related(
                'binding__credential', 'binding__application', 'client__configuration',
                'applied_account',
            ).filter(client=instance, binding__credential_id__in=credentials))
            for credential_id, credential in credentials.items():
                exclude(
                    credential,
                    [state for state in states if state.binding.credential_id == credential_id],
                    reason,
                )
        instance._application_audit_summary = reason
        try:
            return super().update(instance, validated_data)
        finally:
            del instance._application_audit_summary


class CredentialApplicationBindingSerializer(BulkOrgResourceModelSerializer):
    credential = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'key', 'status'),
        label=_('Credential policy')
    )
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'),
        label=_('Integration application')
    )
    clients_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = CredentialApplicationBinding
        fields = [
            'id', 'credential', 'application', 'clients_amount',
            'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = fields


class CredentialFetchSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64, required=False)
    account_id = serializers.UUIDField(required=False)
    configuration_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)

    def validate(self, attrs):
        if bool(attrs.get('key')) == bool(attrs.get('account_id')):
            raise serializers.ValidationError(_('Provide exactly one of key or account_id.'))
        return attrs


class CredentialStateSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=1)
    account_id = serializers.UUIDField()


class CredentialConfirmSerializer(CredentialStateSerializer):
    configuration_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialAgentRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()
    instance_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True)
    client_version = serializers.CharField(max_length=32)
    protocol_version = serializers.IntegerField(min_value=1)
    config_schema_version = serializers.IntegerField(min_value=1)


class CredentialRevisionSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=0)


class CredentialAgentSyncSerializer(serializers.Serializer):
    config_digest = serializers.CharField(max_length=64, required=False, allow_blank=True)
    credentials = CredentialRevisionSerializer(many=True, required=False, default=list)
    delivered_credentials = CredentialRevisionSerializer(many=True, required=False, default=list)
    sync_status = serializers.ChoiceField(
        choices=['', 'success', 'error'], required=False, default='', allow_blank=True,
    )
    sync_error = serializers.CharField(max_length=128, required=False, default='', allow_blank=True)


class ClientAccessConfigurationSerializer(BulkOrgResourceModelSerializer):
    application = ObjectRelatedField(queryset=IntegrationApplication.objects, attrs=('id', 'name'))
    credentials = ObjectRelatedField(
        queryset=ApplicationCredential.objects, many=True,
        attrs=('id', 'name', 'key', 'mode', 'status'),
    )
    removal_reason = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=512,
    )
    instances_amount = serializers.IntegerField(read_only=True)
    online_instances_amount = serializers.IntegerField(read_only=True)
    last_reported = serializers.DateTimeField(read_only=True)

    class Meta:
        model = ClientAccessConfiguration
        fields_mini = ['id', 'name', 'type']
        fields_small = fields_mini + [
            'application', 'credentials', 'is_active', 'instances_amount',
            'online_instances_amount', 'last_reported',
        ]
        fields = fields_small + [
            'language', 'app_user', 'install_path', 'delivery_mode',
            'systemd_unit', 'systemd_action',
            'removal_reason', 'date_created', 'date_updated', 'created_by', 'comment',
        ]
        read_only_fields = ['instances_amount', 'online_instances_amount']

    @classmethod
    def setup_eager_loading(cls, queryset):
        online_after = timezone.now() - timezone.timedelta(minutes=2)
        return queryset.select_related('application').prefetch_related('credentials').annotate(
            instances_amount=Count('instances', distinct=True),
            last_reported=Max('instances__date_last_seen'),
            online_instances_amount=Count(
                'instances', filter=Q(
                    instances__is_active=True, is_active=True, application__is_active=True,
                    instances__date_last_seen__gte=online_after,
                ), distinct=True,
            ),
        )

    def validate(self, attrs):
        if self.instance:
            for field in ('application', 'type'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(_('The application and access type cannot be changed.'))
            if 'credentials' in attrs:
                old = set(self.instance.credentials.values_list('id', flat=True))
                new = {credential.id for credential in attrs['credentials']}
                rotating = self.instance.credentials.filter(id__in=old - new).exclude(status='idle')
                if rotating.exists() and not attrs.get('removal_reason', '').strip():
                    raise serializers.ValidationError({
                        'removal_reason': _(
                            'Explain why the rotating credential should stop participating.'
                        )
                    })
        else:
            attrs.pop('removal_reason', None)
        application = attrs.get('application') or getattr(self.instance, 'application', None)
        credentials = attrs.get('credentials')
        if credentials is None:
            credentials = getattr(self.instance, 'credentials', ApplicationCredential.objects.none()).all()
        if not credentials:
            raise serializers.ValidationError({'credentials': _('Select at least one credential.')})
        allowed_ids = set(application.get_accounts().values_list('id', flat=True)) if application else set()
        for credential in credentials:
            if not credential.applications.filter(id=application.id).exists():
                raise serializers.ValidationError({
                    'credentials': _('The selected credential policy is not bound to this application.')
                })
            required = {credential.account_id, credential.alternate_account_id} - {None}
            if (
                credential.mode == ApplicationCredential.Mode.alternating_rotation
                and not required.issubset(allowed_ids)
            ):
                raise serializers.ValidationError({
                    'credentials': _('The application is not authorized for every selected credential account.')
                })
        access_type = attrs.get('type', getattr(self.instance, 'type', None))
        if (
            access_type == CredentialClientInstance.Type.sdk
            and len({credential.mode for credential in credentials}) > 1
        ):
            raise serializers.ValidationError({
                'credentials': _('SDK access configurations cannot mix credential policy modes.')
            })
        if access_type == CredentialClientInstance.Type.sdk:
            attrs['language'] = 'python'
        elif not attrs.get('app_user', getattr(self.instance, 'app_user', '')):
            raise serializers.ValidationError({'app_user': _('This field is required for Agent access.')})
        path = attrs.get('install_path', getattr(self.instance, 'install_path', '/opt/jumpserver-pam'))
        if not path.startswith('/') or path == '/' or any(char in path for char in '\n\r\x00'):
            raise serializers.ValidationError({'install_path': _('Enter an absolute installation directory.')})
        delivery_mode = attrs.get(
            'delivery_mode', getattr(self.instance, 'delivery_mode', ClientAccessConfiguration.DeliveryMode.json)
        )
        systemd_unit = attrs.get('systemd_unit', getattr(self.instance, 'systemd_unit', '')).strip()
        if access_type == CredentialClientInstance.Type.agent and delivery_mode == ClientAccessConfiguration.DeliveryMode.environment:
            if not SYSTEMD_UNIT.fullmatch(systemd_unit):
                raise serializers.ValidationError({
                    'systemd_unit': _('Enter one systemd .service unit name.')
                })
        else:
            attrs['systemd_unit'] = ''
        return attrs

    def update(self, instance, validated_data):
        instance._credential_removal_reason = validated_data.pop('removal_reason', '').strip()
        try:
            return super().update(instance, validated_data)
        finally:
            del instance._credential_removal_reason
