from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org


__all__ = [
    'TicketMetaApplyAssetSerializer',
    'TicketMetaApplyAssetApplySerializer',
    'TicketMetaApplyAssetApproveSerializer',
]


class TicketMetaApplyAssetSerializer(serializers.Serializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        child=serializers.IPAddressField(), allow_null=True, default=list, label=_('IP group')
    )
    apply_hostname_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('Hostname group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), allow_null=True, default=list, label=_('System user group')
    )
    apply_actions = ActionsField(
        choices=Action.DB_CHOICES, allow_null=True, default=Action.ALL
    )
    apply_date_start = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Date expired')
    )
    # 审批信息
    approve_assets = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True, label=_('Approve assets')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_null=True, label=_('Approve system users')
    )
    approve_actions = ActionsField(
        choices=Action.DB_CHOICES, allow_null=True, default=Action.NONE
    )
    approve_date_start = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Date expired')
    )

    def get_ignore_fields(self, fields):
        return []

    def get_fields(self):
        fields = super().get_fields()
        ignore_fields = self.get_ignore_fields(fields)
        for field in ignore_fields:
            fields.pop(field, None)
        return fields


class TicketMetaApplyAssetApplySerializer(TicketMetaApplyAssetSerializer):

    def get_ignore_fields(self, fields):
        ignore_fields = [
            field_name for field_name in fields.keys() if not field_name.startswith('apply_')
        ]
        return ignore_fields


class TicketMetaApplyAssetApproveSerializer(TicketMetaApplyAssetSerializer):

    def get_ignore_fields(self, fields):
        ignore_fields = [
            field_name for field_name in fields.keys() if not field_name.startswith('approve_')
        ]
        return ignore_fields

    def validate_approve_assets(self, approve_assets_id):
        org_id = self.root.instance.org_id
        org_name = self.root.instance.org_name
        with tmp_to_org(org_id):
            approve_assets = Asset.objects.filter(id__in=approve_assets_id)
        if len(approve_assets) != len(approve_assets_id):
            exists_assets_id = approve_assets.values_list('id', flat=True)
            not_exists_assets_id = set(approve_assets_id) - set(exists_assets_id)
            error = _(
                'These approved assets {} do not exist in organization `{}`'
                ''.format([str(asset_id) for asset_id in not_exists_assets_id], org_name)
            )
            raise serializers.ValidationError(error)
        return approve_assets_id

    def validate_approve_system_users(self, approve_system_users_id):
        org_id = self.root.instance.org_id
        org_name = self.root.instance.org_name
        with tmp_to_org(org_id):
            approve_system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
        if len(approve_system_users) != len(approve_system_users_id):
            exists_system_users_id = approve_system_users.values_list('id', flat=True)
            not_exists_system_users_id = set(approve_system_users_id) - set(exists_system_users_id)
            error = _(
                'These approved system users {} do not exist in organization `{}`'
                ''.format(
                    [str(system_user_id) for system_user_id in not_exists_system_users_id],
                    org_name
                )
            )
            raise serializers.ValidationError(error)
        return approve_system_users_id
