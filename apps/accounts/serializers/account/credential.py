from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import (
    Account, CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, CredentialPolicy, IntegrationApplication,
)
from common.serializers.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = [
    'CredentialPolicySerializer', 'CredentialApplicationBindingSerializer',
    'CredentialClientInstanceSerializer', 'CredentialClientStatusSerializer',
    'CredentialFetchSerializer', 'CredentialHeartbeatSerializer',
    'CredentialConfirmSerializer', 'CredentialAgentRegisterSerializer',
]


class CredentialPolicySerializer(BulkOrgResourceModelSerializer):
    primary_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username'),
        label=_('Primary account')
    )
    backup_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username'),
        label=_('Backup account')
    )
    published_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
        label=_('Published account')
    )
    asset = serializers.SerializerMethodField(label=_('Asset'))
    applications_amount = serializers.IntegerField(read_only=True)
    blockers = serializers.SerializerMethodField(label=_('Blockers'))

    class Meta:
        model = CredentialPolicy
        fields_mini = ['id', 'name', 'key']
        fields_small = fields_mini + [
            'asset', 'primary_account', 'backup_account', 'published_account',
            'revision', 'status', 'is_active',
        ]
        fields = fields_small + [
            'applications_amount', 'blockers', 'primary_version_at_start',
            'rotation_cancelled', 'date_rotation_started', 'date_last_rotated',
            'date_created', 'date_updated', 'created_by', 'comment',
        ]
        read_only_fields = [
            'key', 'published_account', 'revision', 'status',
            'applications_amount', 'blockers', 'primary_version_at_start',
            'rotation_cancelled', 'date_rotation_started', 'date_last_rotated',
        ]

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
        if instance.status == CredentialPolicy.Status.idle:
            return []
        return instance.get_blockers()

    def validate(self, attrs):
        primary = attrs.get('primary_account') or getattr(self.instance, 'primary_account', None)
        backup = attrs.get('backup_account') or getattr(self.instance, 'backup_account', None)
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
        if self.instance and self.instance.status != CredentialPolicy.Status.idle:
            changed = any(
                field in attrs and getattr(self.instance, f'{field}_id') != attrs[field].id
                for field in ('primary_account', 'backup_account')
            )
            if changed:
                raise serializers.ValidationError(_('Accounts cannot be changed during rotation.'))
        return attrs

    def create(self, validated_data):
        validated_data['published_account'] = validated_data['primary_account']
        return super().create(validated_data)


class CredentialClientStatusSerializer(serializers.ModelSerializer):
    policy = serializers.SerializerMethodField(label=_('Credential policy'))
    applied_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'), label=_('Applied account')
    )

    class Meta:
        model = CredentialClientStatus
        fields = [
            'id', 'policy', 'fetched_revision', 'applied_revision',
            'applied_account', 'required_revision', 'is_rotation_participant',
            'date_last_seen', 'date_fetched', 'date_applied',
        ]
        read_only_fields = fields

    @staticmethod
    def get_policy(instance):
        policy = instance.binding.policy
        return {'id': str(policy.id), 'name': policy.name, 'key': policy.key}


class CredentialClientInstanceSerializer(BulkOrgResourceModelSerializer):
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'), label=_('Integration application')
    )
    online = serializers.SerializerMethodField(label=_('Online'))
    credential_statuses = CredentialClientStatusSerializer(many=True, read_only=True)

    class Meta:
        model = CredentialClientInstance
        fields_mini = ['id', 'instance_id', 'type']
        fields_small = fields_mini + [
            'application', 'online', 'date_last_seen', 'is_active',
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
    policy = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'key', 'status'),
        label=_('Credential policy')
    )
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'credential_access_mode'),
        label=_('Integration application')
    )
    clients_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = CredentialApplicationBinding
        fields = [
            'id', 'policy', 'application', 'clients_amount',
            'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = fields


class CredentialFetchSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialStateSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=1)
    account_id = serializers.UUIDField()


class CredentialHeartbeatSerializer(serializers.Serializer):
    instance_id = serializers.CharField(max_length=128, required=False)
    credentials = CredentialStateSerializer(many=True)


class CredentialConfirmSerializer(CredentialStateSerializer):
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialAgentRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()
    instance_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True)
