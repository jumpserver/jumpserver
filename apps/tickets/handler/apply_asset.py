from .base import BaseHandler
from django.utils.translation import ugettext as _

from perms.models import AssetPermission, Action
from assets.models import Asset, SystemUser
from orgs.utils import tmp_to_org, tmp_to_root_org


class Handler(BaseHandler):

    def _on_approve(self):
        super()._on_approve()
        self._create_asset_permission()

    # display
    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_actions_display']
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_actions_display = Action.value_to_choices_display(apply_actions)
        meta_display_values = [apply_actions_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    def _construct_meta_display_of_approve(self):
        meta_display_fields = [
            'approve_actions_display', 'approve_assets_display', 'approve_system_users_display'
        ]
        approve_actions = self.ticket.meta.get('approve_actions', Action.NONE)
        approve_actions_display = Action.value_to_choices_display(approve_actions)
        approve_assets_id = self.ticket.meta.get('approve_assets', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        with tmp_to_org(self.ticket.org_id):
            assets = Asset.objects.filter(id__in=approve_assets_id)
            system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
            approve_assets_display = [str(asset) for asset in assets]
            approve_system_users_display = [str(system_user) for system_user in system_users]
        meta_display_values = [
            approve_actions_display, approve_assets_display, approve_system_users_display
        ]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    # body
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
            _('Applied IP group'), apply_ip_group,
            _("Applied hostname group"), apply_hostname_group,
            _("Applied system user group"), apply_system_user_group,
            _("Applied actions"), apply_actions_display,
            _('Applied date start'), apply_date_start,
            _('Applied date expired'), apply_date_expired,
        )
        return applied_body

    def _construct_meta_body_of_approve(self):
        approve_assets_display = self.ticket.meta.get('approve_assets_display', [])
        approve_system_users_display = self.ticket.meta.get('approve_system_users_display', [])
        approve_actions_display = self.ticket.meta.get('approve_actions_display', [])
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            _('Approved assets'), approve_assets_display,
            _('Approved system users'), approve_system_users_display,
            _('Approved actions'), ', '.join(approve_actions_display),
            _('Approved date start'), approve_date_start,
            _('Approved date expired'), approve_date_expired,
        )
        return approved_body

    # permission
    def _create_asset_permission(self):
        with tmp_to_root_org():
            asset_permission = AssetPermission.objects.filter(id=self.ticket.id).first()
            if asset_permission:
                return asset_permission

        approve_permission_name = self.ticket.meta.get('approve_permission_name', )
        approve_assets_id = self.ticket.meta.get('approve_assets', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        approve_actions = self.ticket.meta.get('approve_actions', Action.NONE)
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        permission_created_by = '{}:{}'.format(
            str(self.ticket.__class__.__name__), str(self.ticket.id)
        )
        permission_comment = _(
            'Created by the ticket, '
            'ticket title: {}, '
            'ticket applicant: {}, '
            'ticket processor: {}, '
            'ticket ID: {}'
        ).format(
            self.ticket.title,
            self.ticket.applicant_display,
            self.ticket.processor_display,
            str(self.ticket.id)
        )

        permission_data = {
            'id': self.ticket.id,
            'name': approve_permission_name,
            'comment': str(permission_comment),
            'created_by': permission_created_by,
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
