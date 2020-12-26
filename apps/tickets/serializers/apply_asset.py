from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from perms.serializers import ActionsField
from perms.models import Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org


__all__ = [
    'TicketApplyAssetSerializer', 'TicketNoMetaSerializer'
]


class TicketApplyAssetSerializer(serializers.Serializer):
    # 申请信息
    apply_ip_group = serializers.ListField(
        child=serializers.IPAddressField(), default=list, label=_('IP group')
    )
    apply_hostname_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('Hostname group')
    )
    apply_system_user_group = serializers.ListField(
        child=serializers.CharField(), default=list, label=_('System user group')
    )
    apply_actions = ActionsField(
        choices=Action.DB_CHOICES, default=Action.ALL
    )
    apply_date_start = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date start')
    )
    apply_date_expired = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date expired')
    )
    # 审批信息
    approve_assets = serializers.ListField(
        child=serializers.UUIDField(), default=list, required=False, label=_('Approve assets')
    )
    approve_system_users = serializers.ListField(
        child=serializers.UUIDField(), default=list, required=False, label=_('Approve system users')
    )
    approve_actions = ActionsField(
        choices=Action.DB_CHOICES, default=Action.NONE
    )
    approve_date_start = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date start')
    )
    approve_date_expired = serializers.DateTimeField(
        allow_null=True, required=False, label=_('Date expired')
    )
    # 辅助信息
    # assets_waitlist_url = serializers.SerializerMethodField()
    # system_users_waitlist_url = serializers.SerializerMethodField()

    def validate_approve_assets(self, approve_assets_id):
        if not self.root.view_action_is_approve:
            return approve_assets_id
        if not approve_assets_id:
            error = _('The approved assets cannot be empty')
            raise serializers.ValidationError(error)
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
        if not self.root.view_action_is_approve:
            return approve_system_users_id
        if not approve_system_users_id:
            error = _('The approved system users cannot be empty')
            raise serializers.ValidationError(error)
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

    @staticmethod
    def perform_apply_validate(attrs):
        return {
            name: value
            for name, value in attrs.items()
            if name.startswith('apply_')
        }

    @staticmethod
    def perform_approve_validate(attrs):
        return {
            name: value
            for name, value in attrs.items()
            if name.startswith('approve_')
        }

    def validate(self, attrs):
        perform_view_action_validate_method = getattr(
            self, f'perform_{self.root.view_action}_validate', None
        )
        if perform_view_action_validate_method:
            attrs = perform_view_action_validate_method(attrs)
        else:
            attrs = {}
        return attrs


class TicketNoMetaSerializer(serializers.Serializer):
    pass
