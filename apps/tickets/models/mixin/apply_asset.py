from django.utils.translation import ugettext as __

from perms.models import AssetPermission, Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org, tmp_to_root_org


class ConstructBodyMixin:
    def construct_apply_asset_applied_body(self):
        apply_ip_group = self.meta['apply_ip_group']
        apply_hostname_group = self.meta['apply_hostname_group']
        apply_system_user_group = self.meta['apply_system_user_group']
        apply_actions = self.meta['apply_actions']
        apply_actions_display = Action.value_to_choices_display(apply_actions)
        apply_actions_display = [str(action_display) for action_display in apply_actions_display]
        apply_date_start = self.meta['apply_date_start']
        apply_date_expired = self.meta['apply_date_expired']
        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            __('Applied IP group'), apply_ip_group,
            __("Applied hostname group"), apply_hostname_group,
            __("Applied system user group"), apply_system_user_group,
            __("Applied actions"), apply_actions_display,
            __('Applied date start'), apply_date_start,
            __('Applied date expired'), apply_date_expired,
        )
        return applied_body

    def construct_apply_asset_approved_body(self):
        approve_assets_id = self.meta['approve_assets']
        approve_system_users_id = self.meta['approve_system_users']
        with tmp_to_org(self.org_id):
            approve_assets = Asset.objects.filter(id__in=approve_assets_id)
            approve_system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
        approve_assets_display = [str(asset) for asset in approve_assets]
        approve_system_users_display = [str(system_user) for system_user in approve_system_users]
        approve_actions = self.meta['approve_actions']
        approve_actions_display = Action.value_to_choices_display(approve_actions)
        approve_actions_display = [str(action_display) for action_display in approve_actions_display]
        approve_date_start = self.meta['approve_date_start']
        approve_date_expired = self.meta['approve_date_expired']
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            __('Approved assets'), ', '.join(approve_assets_display),
            __('Approved system users'), ', '.join(approve_system_users_display),
            __('Approved actions'), ', '.join(approve_actions_display),
            __('Approved date start'), approve_date_start,
            __('Approved date expired'), approve_date_expired,
        )
        return approved_body


class CreatePermissionMixin:
    def create_apply_asset_permission(self):
        with tmp_to_root_org():
            asset_permission = AssetPermission.objects.filter(id=self.id).first()
            if asset_permission:
                return asset_permission
        approve_assets_id = self.meta['approve_assets']
        approve_system_users_id = self.meta['approve_system_users']
        approve_actions = self.meta['approve_actions']
        approve_date_start = self.meta['approve_date_start']
        approve_date_expired = self.meta['approve_date_expired']
        permission_name = '{}({})'.format(
            __('Created by ticket ({})'.format(self.title)), str(self.id)[:4]
        )
        permission_comment = __(
            'Created by the ticket, '
            'ticket title: {}, '
            'ticket applicant: {}, '
            'ticket processor: {}, '
            'ticket ID: {}'
            ''.format(self.title, self.applicant_display, self.processor_display, str(self.id))
        )
        permission_data = {
            'id': self.id,
            'name': permission_name,
            'created_by': self.processor_display,
            'comment': permission_comment,
            'actions': approve_actions,
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.org_id):
            asset_permission = AssetPermission.objects.create(**permission_data)
            asset_permission.users.add(self.applicant)
            asset_permission.assets.set(approve_assets_id)
            asset_permission.system_users.set(approve_system_users_id)
        return asset_permission
