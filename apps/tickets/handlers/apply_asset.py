from django.utils.translation import ugettext as _

from perms.models import AssetPermission
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import ApplyAssetTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyAssetTicket

    def _on_step_approved(self, step):
        is_finished = super()._on_step_approved(step)
        if is_finished:
            self._create_asset_permission()

    def _construct_meta_body_of_open(self):
        apply_nodes = self.ticket.rel_snapshot['apply_nodes']
        apply_assets = self.ticket.rel_snapshot['apply_assets']
        apply_system_users = self.ticket.rel_snapshot['apply_system_users']
        apply_actions_display = self.ticket.apply_actions_display
        apply_date_start = self.ticket.apply_date_start
        apply_date_expired = self.ticket.apply_date_expired
        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            _("Applied node group"), ','.join(apply_nodes),
            _("Applied hostname group"), ','.join(apply_assets),
            _("Applied system user group"), ','.join(apply_system_users),
            _("Applied actions"), ','.join(apply_actions_display),
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

        apply_permission_name = self.ticket.apply_permission_name
        apply_nodes = self.ticket.apply_nodes.all()
        apply_assets = self.ticket.apply_assets.all()
        apply_system_users = self.ticket.apply_system_users.all()
        apply_actions = self.ticket.apply_actions
        apply_date_start = self.ticket.apply_date_start
        apply_date_expired = self.ticket.apply_date_expired
        permission_created_by = '{}:{}'.format(
            str(self.ticket.__class__.__name__), str(self.ticket.id)
        )
        permission_comment = _(
            'Created by the ticket '
            'ticket title: {} '
            'ticket applicant: {} '
            'ticket processor: {} '
            'ticket ID: {}'
        ).format(
            self.ticket.title,
            self.ticket.applicant,
            ','.join([i['processor_display'] for i in self.ticket.process_map]),
            str(self.ticket.id)
        )

        permission_data = {
            'id': self.ticket.id,
            'name': apply_permission_name,
            'from_ticket': True,
            'comment': str(permission_comment),
            'created_by': permission_created_by,
            'actions': apply_actions,
            'date_start': apply_date_start,
            'date_expired': apply_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            asset_permission = AssetPermission.objects.create(**permission_data)
            asset_permission.users.add(self.ticket.applicant)
            print(apply_nodes)
            asset_permission.nodes.set(apply_nodes)
            asset_permission.assets.set(apply_assets)
            asset_permission.system_users.set(apply_system_users)

        return asset_permission
