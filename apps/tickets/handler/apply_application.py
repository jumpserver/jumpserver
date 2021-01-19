from django.utils.translation import ugettext as _
from orgs.utils import tmp_to_org, tmp_to_root_org
from applications.models import Application
from applications.const import ApplicationCategoryChoices, ApplicationTypeChoices
from assets.models import SystemUser
from perms.models import ApplicationPermission
from .base import BaseHandler


class Handler(BaseHandler):

    def _on_approve(self):
        super()._on_approve()
        self._create_application_permission()

    # display
    def _construct_meta_display_of_open(self):
        meta_display_fields = ['apply_category_display', 'apply_type_display']
        apply_category = self.ticket.meta.get('apply_category')
        apply_category_display = ApplicationCategoryChoices.get_label(apply_category)
        apply_type = self.ticket.meta.get('apply_type')
        apply_type_display = ApplicationTypeChoices.get_label(apply_type)
        meta_display_values = [apply_category_display, apply_type_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    def _construct_meta_display_of_approve(self):
        meta_display_fields = ['approve_applications_display', 'approve_system_users_display']
        approve_applications_id = self.ticket.meta.get('approve_applications', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        with tmp_to_org(self.ticket.org_id):
            approve_applications = Application.objects.filter(id__in=approve_applications_id)
            system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
            approve_applications_display = [str(application) for application in approve_applications]
            approve_system_users_display = [str(system_user) for system_user in system_users]
        meta_display_values = [approve_applications_display, approve_system_users_display]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

    # body
    def _construct_meta_body_of_open(self):
        apply_category_display = self.ticket.meta.get('apply_category_display')
        apply_type_display = self.ticket.meta.get('apply_type_display')
        apply_application_group = self.ticket.meta.get('apply_application_group', [])
        apply_system_user_group = self.ticket.meta.get('apply_system_user_group', [])
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
            _('Applied application group'), apply_application_group,
            _('Applied system user group'), apply_system_user_group,
            _('Applied date start'), apply_date_start,
            _('Applied date expired'), apply_date_expired,
        )
        return applied_body

    def _construct_meta_body_of_approve(self):
        # 审批信息
        approve_applications_display = self.ticket.meta.get('approve_applications_display', [])
        approve_system_users_display = self.ticket.meta.get('approve_system_users_display', [])
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            _('Approved applications'), approve_applications_display,
            _('Approved system users'), approve_system_users_display,
            _('Approved date start'), approve_date_start,
            _('Approved date expired'), approve_date_expired
        )
        return approved_body

    # permission
    def _create_application_permission(self):
        with tmp_to_root_org():
            application_permission = ApplicationPermission.objects.filter(id=self.ticket.id).first()
            if application_permission:
                return application_permission

        apply_category = self.ticket.meta.get('apply_category')
        apply_type = self.ticket.meta.get('apply_type')
        approve_permission_name = self.ticket.meta.get('approve_permission_name', '')
        approved_applications_id = self.ticket.meta.get('approve_applications', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
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
        permissions_data = {
            'id': self.ticket.id,
            'name': approve_permission_name,
            'category': apply_category,
            'type': apply_type,
            'comment': str(permission_comment),
            'created_by': permission_created_by,
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            application_permission = ApplicationPermission.objects.create(**permissions_data)
            application_permission.users.add(self.ticket.applicant)
            application_permission.applications.set(approved_applications_id)
            application_permission.system_users.set(approve_system_users_id)

        return application_permission
