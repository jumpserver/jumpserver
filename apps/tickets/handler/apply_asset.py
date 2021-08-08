from assets.models import Asset
from assets.models import SystemUser

from .base import BaseHandler
from django.utils.translation import ugettext as _

from perms.models import AssetPermission, Action
from orgs.utils import tmp_to_org, tmp_to_root_org


class Handler(BaseHandler):

    def _on_approve(self):
        is_finish = super()._on_approve()
        if is_finish:
            self._create_asset_permission()

    # display
    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_actions_display']
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_actions_display = Action.value_to_choices_display(apply_actions)
        meta_display_values = [apply_actions_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        apply_assets = self.ticket.meta.get('apply_assets')
        apply_system_users = self.ticket.meta.get('apply_system_users')
        meta_display.update({
            'apply_assets_display': [str(i) for i in Asset.objects.filter(id__in=apply_assets)],
            'apply_system_users_display': [str(i)for i in SystemUser.objects.filter(id__in=apply_system_users)]
        })
        return meta_display

    # body
    def _construct_meta_body_of_open(self):
        apply_assets = self.ticket.meta.get('apply_assets', [])
        apply_system_users = self.ticket.meta.get('apply_system_users', [])
        apply_actions_display = self.ticket.meta.get('apply_actions_display', [])
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            _("Applied hostname group"), apply_assets,
            _("Applied system user group"), apply_system_users,
            _("Applied actions"), apply_actions_display,
            _('Applied date start'), apply_date_start,
            _('Applied date expired'), apply_date_expired,
        )
        return applied_body

    # permission
    def _create_asset_permission(self):
        with tmp_to_root_org():
            asset_permission = AssetPermission.objects.filter(id=self.ticket.id).first()
            if asset_permission:
                return asset_permission

        apply_permission_name = self.ticket.meta.get('apply_permission_name', )
        apply_assets = self.ticket.meta.get('apply_assets', [])
        apply_system_users = self.ticket.meta.get('apply_system_users', [])
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
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
            str(self.ticket.processor),
            str(self.ticket.id)
        )

        permission_data = {
            'id': self.ticket.id,
            'name': apply_permission_name,
            'comment': str(permission_comment),
            'created_by': permission_created_by,
            'actions': apply_actions,
            'date_start': apply_date_start,
            'date_expired': apply_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            asset_permission = AssetPermission.objects.create(**permission_data)
            asset_permission.users.add(self.ticket.applicant)
            asset_permission.assets.set(apply_assets)
            asset_permission.system_users.set(apply_system_users)

        return asset_permission
