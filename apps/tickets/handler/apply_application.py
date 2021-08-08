from django.utils.translation import ugettext as _
from orgs.utils import tmp_to_org, tmp_to_root_org
from applications.const import AppCategory, AppType
from applications.models import Application
from perms.models import ApplicationPermission
from assets.models import SystemUser

from .base import BaseHandler


class Handler(BaseHandler):

    def _on_approve(self):
        is_finish = super()._on_approve()
        if is_finish:
            self._create_application_permission()

    # display
    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_category_display', 'apply_type_display']
        apply_category = self.ticket.meta.get('apply_category')
        apply_category_display = AppCategory.get_label(apply_category)
        apply_type = self.ticket.meta.get('apply_type')
        apply_type_display = AppType.get_label(apply_type)
        meta_display_values = [apply_category_display, apply_type_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        apply_system_users = self.ticket.meta.get('apply_system_users')
        apply_applications = self.ticket.meta.get('apply_applications')
        meta_display.update({
            'apply_system_users_display': [str(i) for i in SystemUser.objects.filter(id__in=apply_system_users)],
            'apply_applications_display': [str(i) for i in Application.objects.filter(id__in=apply_applications)]
        })

        return meta_display

    # body
    def _construct_meta_body_of_open(self):
        apply_category_display = self.ticket.meta.get('apply_category_display')
        apply_type_display = self.ticket.meta.get('apply_type_display')
        apply_applications = self.ticket.meta.get('apply_applications', [])
        apply_system_users = self.ticket.meta.get('apply_system_users', [])
        apply_date_start = self.ticket.meta.get('apply_date_start')
        apply_date_expired = self.ticket.meta.get('apply_date_expired')
        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            _('Applied category'), apply_category_display,
            _('Applied type'), apply_type_display,
            _('Applied application group'), apply_applications,
            _('Applied system user group'), apply_system_users,
            _('Applied date start'), apply_date_start,
            _('Applied date expired'), apply_date_expired,
        )
        return applied_body

    # permission
    def _create_application_permission(self):
        with tmp_to_root_org():
            application_permission = ApplicationPermission.objects.filter(id=self.ticket.id).first()
            if application_permission:
                return application_permission

        apply_category = self.ticket.meta.get('apply_category')
        apply_type = self.ticket.meta.get('apply_type')
        apply_permission_name = self.ticket.meta.get('apply_permission_name', '')
        apply_applications = self.ticket.meta.get('apply_applications', [])
        apply_system_users = self.ticket.meta.get('apply_system_users', [])
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
        permissions_data = {
            'id': self.ticket.id,
            'name': apply_permission_name,
            'category': apply_category,
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
