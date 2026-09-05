from django.db.models import Count, Max, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import (
    Account, CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, ApplicationCredential, IntegrationApplication,
    ClientAccessConfiguration, CredentialRotationRecord,
)
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = [
    'ApplicationCredentialSerializer', 'CredentialApplicationBindingSerializer',
    'CredentialClientInstanceSerializer', 'CredentialClientStatusSerializer',
    'CredentialFetchSerializer', 'CredentialHeartbeatSerializer',
    'CredentialConfirmSerializer', 'CredentialAgentRegisterSerializer',
    'ClientAccessConfigurationSerializer', 'CredentialRotationRecordSerializer',
]


class ApplicationCredentialSerializer(BulkOrgResourceModelSerializer):
    primary_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username', 'secret_type'),
        label=_('Primary account')
    )
    backup_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username'),
        label=_('Backup account'), required=False, allow_null=True
    )
    published_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
        label=_('Published account')
    )
    asset = serializers.SerializerMethodField(label=_('Asset'))
    applications_amount = serializers.IntegerField(read_only=True)
    blockers = serializers.SerializerMethodField(label=_('Blockers'))
    applications = ObjectRelatedField(
        read_only=True, many=True,
        attrs=('id', 'name'), label=_('Integration applications')
    )
    last_fetched = serializers.DateTimeField(read_only=True)
    change_execution = ObjectRelatedField(read_only=True, attrs=('id', 'status', 'date_finished'))

    class Meta:
        model = ApplicationCredential
        fields_mini = ['id', 'name', 'key']
        fields_small = fields_mini + [
            'type', 'rotation_mode', 'asset', 'primary_account', 'backup_account',
            'published_account', 'revision', 'status', 'is_active',
            'last_fetched', 'date_last_rotated', 'applications_amount',
        ]
        fields = fields_small + [
            'applications', 'change_execution', 'blockers', 'primary_version_at_start',
            'rotation_cancelled', 'date_rotation_started',
            'date_created', 'date_updated', 'created_by', 'comment',
        ]
        read_only_fields = [
            'key', 'published_account', 'revision', 'status',
            'applications_amount', 'blockers', 'primary_version_at_start',
            'rotation_cancelled', 'date_rotation_started', 'date_last_rotated',
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related(
            'primary_account__asset__platform', 'backup_account', 'published_account', 'change_execution'
        ).prefetch_related('applications').annotate(
            applications_amount=Count('access_configurations__application', distinct=True),
            last_fetched=Max('application_bindings__client_statuses__date_fetched'),
        )

    @staticmethod
    def get_asset(instance):
        asset = instance.asset
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
        if self.instance and self.instance.status != ApplicationCredential.Status.idle:
            for field in ('type', 'rotation_mode', 'primary_account', 'backup_account', 'is_active'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(_('Credential settings cannot be changed during rotation.'))
        primary = attrs.get('primary_account') or getattr(self.instance, 'primary_account', None)
        credential_type = attrs.get('type') or getattr(self.instance, 'type', ApplicationCredential.Type.rotation)
        rotation_mode = attrs.get('rotation_mode') or getattr(self.instance, 'rotation_mode', ApplicationCredential.RotationMode.dual)
        backup = attrs.get('backup_account', getattr(self.instance, 'backup_account', None))
        if credential_type == ApplicationCredential.Type.fixed:
            attrs['rotation_mode'] = ''
            attrs['backup_account'] = None
            return attrs
        if rotation_mode == ApplicationCredential.RotationMode.dual and not backup:
            raise serializers.ValidationError({'backup_account': _('This field is required for dual-account rotation.')})
        if rotation_mode == ApplicationCredential.RotationMode.single:
            attrs['backup_account'] = None
            return attrs
        if not rotation_mode:
            raise serializers.ValidationError({'rotation_mode': _('This field is required.')})
        if not primary or not backup:
            return attrs
        if primary.id == backup.id:
            raise serializers.ValidationError(_('Primary and backup accounts must be different.'))
        if primary.asset_id != backup.asset_id:
            raise serializers.ValidationError(_('Primary and backup accounts must belong to the same asset.'))
        if primary.org_id != backup.org_id:
            raise serializers.ValidationError(_('Primary and backup accounts must belong to the same organization.'))
        if primary.secret_type != backup.secret_type:
            raise serializers.ValidationError(_('Primary and backup accounts must use the same secret type.'))
        return attrs

    def create(self, validated_data):
        validated_data['published_account'] = validated_data['primary_account']
        return super().create(validated_data)

    def update(self, instance, validated_data):
        primary = validated_data.get('primary_account', instance.primary_account)
        if primary.id != instance.primary_account_id:
            validated_data['published_account'] = primary
            validated_data['revision'] = instance.revision + 1
        return super().update(instance, validated_data)


class CredentialClientStatusSerializer(serializers.ModelSerializer):
    credential = serializers.SerializerMethodField(label=_('Application credential'))
    applied_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'), label=_('Applied account')
    )

    class Meta:
        model = CredentialClientStatus
        fields = [
            'id', 'credential', 'fetched_revision', 'applied_revision',
            'applied_account', 'required_revision', 'is_rotation_participant',
            'date_last_seen', 'date_fetched', 'date_applied',
        ]
        read_only_fields = fields

    @staticmethod
    def get_credential(instance):
        credential = instance.binding.credential
        return {'id': str(credential.id), 'name': credential.name, 'key': credential.key}


class CredentialClientInstanceSerializer(BulkOrgResourceModelSerializer):
    configuration = ObjectRelatedField(read_only=True, attrs=('id', 'name'))
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'), label=_('Integration application')
    )
    online = serializers.SerializerMethodField(label=_('Online'))
    credential_statuses = CredentialClientStatusSerializer(many=True, read_only=True)

    class Meta:
        model = CredentialClientInstance
        fields_mini = ['id', 'instance_id', 'type']
        fields_small = fields_mini + [
            'application', 'configuration', 'online', 'date_last_seen', 'is_active',
        ]
        fields = fields_small + [
            'credential_statuses', 'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = [
            'id', 'instance_id', 'type', 'application', 'online',
            'date_last_seen', 'credential_statuses', 'date_created', 'date_updated',
        ]

    @staticmethod
    def get_online(instance):
        return instance.online


class CredentialApplicationBindingSerializer(BulkOrgResourceModelSerializer):
    credential = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'key', 'status'),
        label=_('Application credential')
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
    key = serializers.CharField(max_length=64)
    configuration_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialStateSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=1)
    account_id = serializers.UUIDField()


class CredentialHeartbeatSerializer(serializers.Serializer):
    configuration_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)
    credentials = CredentialStateSerializer(many=True)


class CredentialConfirmSerializer(CredentialStateSerializer):
    configuration_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialAgentRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()
    instance_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True)


class ClientAccessConfigurationSerializer(BulkOrgResourceModelSerializer):
    application = ObjectRelatedField(queryset=IntegrationApplication.objects, attrs=('id', 'name'))
    credentials = ObjectRelatedField(
        queryset=ApplicationCredential.objects, many=True, attrs=('id', 'name', 'key', 'type')
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
            'language', 'app_user', 'install_path',
            'date_created', 'date_updated', 'created_by', 'comment',
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
                if self.instance.credentials.filter(id__in=old - new).exclude(status='idle').exists():
                    raise serializers.ValidationError(_('A rotating credential cannot be removed from a configuration.'))
        application = attrs.get('application') or getattr(self.instance, 'application', None)
        credentials = attrs.get('credentials')
        if credentials is None:
            credentials = getattr(self.instance, 'credentials', ApplicationCredential.objects.none()).all()
        if not credentials:
            raise serializers.ValidationError({'credentials': _('Select at least one credential.')})
        allowed_ids = set(application.get_accounts().values_list('id', flat=True)) if application else set()
        for credential in credentials:
            required = {credential.primary_account_id}
            if credential.backup_account_id:
                required.add(credential.backup_account_id)
            if not required.issubset(allowed_ids):
                raise serializers.ValidationError({
                    'credentials': _('The application is not authorized for every selected credential account.')
                })
        if attrs.get('type', getattr(self.instance, 'type', None)) == CredentialClientInstance.Type.sdk:
            attrs['language'] = 'python'
        elif not attrs.get('app_user', getattr(self.instance, 'app_user', '')):
            raise serializers.ValidationError({'app_user': _('This field is required for Agent access.')})
        path = attrs.get('install_path', getattr(self.instance, 'install_path', '/opt/jumpserver-pam'))
        if not path.startswith('/') or path == '/' or any(char in path for char in '\n\r\x00'):
            raise serializers.ValidationError({'install_path': _('Enter an absolute installation directory.')})
        return attrs

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        for credential in instance.credentials.all():
            CredentialApplicationBinding.objects.get_or_create(credential=credential, application=instance.application)
        return instance


class CredentialRotationRecordSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = CredentialRotationRecord
        fields = [
            'id', 'status', 'date_created', 'date_finished', 'created_by', 'comment',
        ]
        read_only_fields = fields
