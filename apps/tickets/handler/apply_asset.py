from .base import BaseHandler
from django.utils.translation import ugettext as __

from perms.models import AssetPermission, Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.utils import convert_model_data_field_name_to_verbose_name


class Handler(BaseHandler):

    def on_approve(self):
        super().on_approve()
        self._create_asset_permission()

    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_actions_display']
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_actions_display = Action.value_to_choices_display(apply_actions)
        meta_display_values = [apply_actions_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    def _construct_meta_display_of_approve(self):
        meta_display_fields = [
            'approve_actions_display', 'approve_assets_snapshot', 'approve_system_users_snapshot'
        ]
        approve_actions = self.ticket.meta.get('approve_actions', Action.NONE)
        approve_actions_display = Action.value_to_choices_display(approve_actions)
        approve_assets_id = self.ticket.meta.get('approve_assets', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        with tmp_to_org(self.ticket.org_id):
            approve_assets_snapshot = list(
                Asset.objects.filter(id__in=approve_assets_id).values(
                    'hostname', 'ip', 'protocols', 'platform__name', 'public_ip'
                )
            )
            approve_system_users_snapshot = list(
                SystemUser.objects.filter(id__in=approve_system_users_id).values(
                    'name', 'username', 'username_same_with_user', 'protocol',
                    'auto_push', 'sudo', 'home', 'sftp_root'
                )
            )
        meta_display_values = [
            approve_actions_display, approve_assets_snapshot, approve_system_users_snapshot
        ]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    def _construct_meta_body_of_open(self):
        apply_ip_group = self.ticket.meta.get('apply_ip_group', [])
        apply_hostname_group = self.ticket.meta.get('apply_hostname_group', [])
        apply_system_user_group = self.ticket.meta.get('apply_system_user_group', [])
        apply_actions_display = self.ticket.meta.get('apply_actions_display', [])
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
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

    def _construct_meta_body_of_approve(self):
        approve_assets_snapshot = self.ticket.meta.get('approve_assets_snapshot', [])
        approve_assets_snapshot_display = convert_model_data_field_name_to_verbose_name(
            model=Asset, data=approve_assets_snapshot
        )
        approve_system_users_snapshot = self.ticket.meta.get('approve_system_users_snapshot', [])
        approve_system_users_snapshot_display = convert_model_data_field_name_to_verbose_name(
            model=SystemUser, data=approve_system_users_snapshot
        )
        approve_actions_display = self.ticket.meta.get('approve_actions_display', [])
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            __('Approved assets'), approve_assets_snapshot_display,
            __('Approved system users'), approve_system_users_snapshot_display,
            __('Approved actions'), ', '.join(approve_actions_display),
            __('Approved date start'), approve_date_start,
            __('Approved date expired'), approve_date_expired,
        )
        return approved_body

    def _create_asset_permission(self):
        with tmp_to_root_org():
            asset_permission = AssetPermission.objects.filter(id=self.ticket.id).first()
            if asset_permission:
                return asset_permission

        approve_assets_id = self.ticket.meta.get('approve_assets', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        approve_actions = self.ticket.meta.get('approve_actions', Action.NONE)
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        permission_name = '{}({})'.format(
            __('Created by ticket ({})'.format(self.ticket.title)), str(self.ticket.id)[:4]
        )
        permission_comment = __(
            'Created by the ticket, '
            'ticket title: {}, '
            'ticket applicant: {}, '
            'ticket processor: {}, '
            'ticket ID: {}'
            ''.format(
                self.ticket.title, self.ticket.applicant_display, self.ticket.processor_display,
                str(self.ticket.id)
            )
        )
        permission_data = {
            'id': self.ticket.id,
            'name': permission_name,
            'comment': permission_comment,
            'created_by': '{}:{}'.format(str(self.__class__.__name__), str(self.ticket.id)),
            'actions': approve_actions,
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            asset_permission = AssetPermission.objects.create(**permission_data)
            asset_permission.users.add(self.ticket.applicant)
            asset_permission.assets.set(approve_assets_id)
            asset_permission.system_users.set(approve_system_users_id)

        return asset_permission
