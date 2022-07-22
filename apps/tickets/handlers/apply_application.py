from django.utils.translation import ugettext as _

from orgs.utils import tmp_to_org
from perms.models import ApplicationPermission
from tickets.models import ApplyApplicationTicket
from .base import BaseHandler


class Handler(BaseHandler):
    ticket: ApplyApplicationTicket

    def _on_step_approved(self, step):
        is_finished = super()._on_step_approved(step)
        if is_finished:
            self._create_application_permission()

    # permission
    def _create_application_permission(self):
        org_id = self.ticket.org_id
        with tmp_to_org(org_id):
            application_permission = ApplicationPermission.objects.filter(id=self.ticket.id).first()
            if application_permission:
                return application_permission

            apply_applications = self.ticket.apply_applications.all()
            apply_system_users = self.ticket.apply_system_users.all()

        apply_permission_name = self.ticket.apply_permission_name
        apply_actions = self.ticket.apply_actions
        apply_category = self.ticket.apply_category
        apply_type = self.ticket.apply_type
        apply_date_start = self.ticket.apply_date_start
        apply_date_expired = self.ticket.apply_date_expired
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
            self.ticket.applicant,
            ','.join([i['processor_display'] for i in self.ticket.process_map]),
            str(self.ticket.id)
        )
        permissions_data = {
            'id': self.ticket.id,
            'name': apply_permission_name,
            'from_ticket': True,
            'category': apply_category,
            'actions': apply_actions,
            'type': apply_type,
            'comment': str(permission_comment),
            'created_by': permission_created_by,
            'date_start': apply_date_start,
            'date_expired': apply_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            application_permission = ApplicationPermission.objects.create(**permissions_data)
            application_permission.users.add(self.ticket.applicant)
            application_permission.applications.set(apply_applications)
            application_permission.system_users.set(apply_system_users)

        return application_permission
