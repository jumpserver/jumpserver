from django.utils.translation import ugettext as _

from assets.models import Node, Asset, SystemUser
from perms.models import AssetPermission, Action
from orgs.utils import tmp_to_org, tmp_to_root_org
from .base import BaseHandler


class Handler(BaseHandler):

    def _on_approve(self):
        is_finished = super()._on_approve()
        if is_finished:
            self._create_asset_permission()

    # display
    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_actions_display']
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_actions_display = Action.value_to_choices_display(apply_actions)
        meta_display_values = [apply_actions_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        apply_nodes = self.ticket.meta.get('apply_nodes', [])
        apply_assets = self.ticket.meta.get('apply_assets', [])
        apply_system_users = self.ticket.meta.get('apply_system_users')
        with tmp_to_org(self.ticket.org_id):
            meta_display.update({
                'apply_nodes_display': [str(i) for i in Node.objects.filter(id__in=apply_nodes)],
                'apply_assets_display': [str(i) for i in Asset.objects.filter(id__in=apply_assets)],
                'apply_system_users_display': [
                    str(i) for i in SystemUser.objects.filter(id__in=apply_system_users)
                ]
            })
        return meta_display

    # body
    def _construct_meta_body_of_open(self):
        apply_nodes = self.ticket.meta.get('apply_nodes_display', [])
        apply_assets = self.ticket.meta.get('apply_assets_display', [])
        apply_system_users = self.ticket.meta.get('apply_system_users_display', [])
        apply_actions_display = self.ticket.meta.get('apply_actions_display', [])
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
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

        apply_permission_name = self.ticket.meta.get('apply_permission_name', )
        apply_nodes = self.ticket.meta.get('apply_nodes', [])
        apply_assets = self.ticket.meta.get('apply_assets', [])
        apply_system_users = self.ticket.meta.get('apply_system_users', [])
        apply_actions = self.ticket.meta.get('apply_actions', Action.NONE)
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
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
            self.ticket.applicant_display,
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
