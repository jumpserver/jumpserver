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

    # permission
    def _create_asset_permission(self):
        org_id = self.ticket.org_id
        with tmp_to_org(org_id):
            asset_permission = AssetPermission.objects.filter(id=self.ticket.id).first()
            if asset_permission:
                return asset_permission

            apply_nodes = self.ticket.apply_nodes.all()
            apply_assets = self.ticket.apply_assets.all()
            apply_system_users = self.ticket.apply_system_users.all()

        apply_permission_name = self.ticket.apply_permission_name
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
            asset_permission.nodes.set(apply_nodes)
            asset_permission.assets.set(apply_assets)
            asset_permission.system_users.set(apply_system_users)

        return asset_permission
