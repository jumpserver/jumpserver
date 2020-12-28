from django.utils.translation import ugettext as __
from orgs.utils import tmp_to_org, tmp_to_root_org
from applications.models import Application, Category
from assets.models import SystemUser
from perms.models import ApplicationPermission


class ConstructBodyMixin:

    def construct_apply_application_applied_body(self):
        apply_category = self.meta['apply_category']
        apply_category_display = dict(Category.choices)[apply_category]
        apply_type = self.meta['apply_type']
        apply_type_display = dict(Category.get_type_choices(apply_category))[apply_type]
        apply_application_group = self.meta['apply_application_group']
        apply_system_user_group = self.meta['apply_system_user_group']
        apply_date_start = self.meta['apply_date_start']
        apply_date_expired = self.meta['apply_date_expired']
        applied_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            __('Applied category'), apply_category_display,
            __('Applied type'), apply_type_display,
            __('Applied application group'), apply_application_group,
            __('Applied system user group'), apply_system_user_group,
            __('Applied date start'), apply_date_start,
            __('Applied date expired'), apply_date_expired,
        )
        return applied_body

    def construct_apply_application_approved_body(self):
        # 审批信息
        approve_applications_id = self.meta['approve_applications']
        approve_system_users_id = self.meta['approve_system_users']
        with tmp_to_org(self.org_id):
            approve_applications = Application.objects.filter(id__in=approve_applications_id)
            approve_system_users = SystemUser.objects.filter(id__in=approve_system_users_id)
        approve_applications_display = [str(application) for application in approve_applications]
        approve_system_users_display = [str(system_user) for system_user in approve_system_users]
        approve_date_start = self.meta['approve_date_start']
        approve_date_expired = self.meta['approve_date_expired']
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            __('Approved applications'), ', '.join(approve_applications_display),
            __('Approved system users'), ', '.join(approve_system_users_display),
            __('Approved date start'), approve_date_start,
            __('Approved date expired'), approve_date_expired
        )
        return approved_body


class CreatePermissionMixin:

    def create_apply_application_permission(self):
        with tmp_to_root_org():
            application_permission = ApplicationPermission.objects.filter(id=self.id).first()
            if application_permission:
                return application_permission

        apply_category = self.meta['apply_category']
        apply_type = self.meta['apply_type']
        approved_applications_id = self.meta['approve_applications']
        approve_system_users_id = self.meta['approve_system_users']
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
        permissions_data = {
            'id': self.id,
            'name': permission_name,
            'category': apply_category,
            'type': apply_type,
            'comment': permission_comment,
            'created_by': self.processor_display,
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.org_id):
            application_permission = ApplicationPermission.objects.create(**permissions_data)
            application_permission.users.add(self.applicant)
            application_permission.applications.set(approved_applications_id)
            application_permission.system_users.set(approve_system_users_id)

        return application_permission
