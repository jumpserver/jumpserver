from django.utils.translation import ugettext as __
from orgs.utils import tmp_to_org, tmp_to_root_org
from applications.models import Application
from applications.const import ApplicationCategoryChoices, ApplicationTypeChoices
from assets.models import SystemUser
from perms.models import ApplicationPermission
from tickets.utils import convert_model_data_field_name_to_verbose_name
from .base import BaseHandler


class Handler(BaseHandler):

    def on_approve(self):
        super().on_approve()
        self._create_application_permission()

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
        meta_display_fields = ['approve_applications_snapshot', 'approve_system_users_snapshot']
        approve_applications_id = self.ticket.meta.get('approve_applications', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
        with tmp_to_org(self.ticket.org_id):
            approve_applications_snapshot = list(
                Application.objects.filter(id__in=approve_applications_id).values(
                    'name', 'category', 'type'
                )
            )
            approve_system_users_snapshot = list(
                SystemUser.objects.filter(id__in=approve_system_users_id).values(
                    'name', 'username', 'username_same_with_user', 'protocol',
                    'auto_push', 'sudo', 'home', 'sftp_root'
                )
            )
        meta_display_values = [approve_applications_snapshot, approve_system_users_snapshot]
        meta_display = dict(zip(meta_display_fields, meta_display_values))
        return meta_display

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
            __('Applied category'), apply_category_display,
            __('Applied type'), apply_type_display,
            __('Applied application group'), apply_application_group,
            __('Applied system user group'), apply_system_user_group,
            __('Applied date start'), apply_date_start,
            __('Applied date expired'), apply_date_expired,
        )
        return applied_body

    def _construct_meta_body_of_approve(self):
        # 审批信息
        approve_applications_snapshot = self.ticket.meta.get('approve_applications_snapshot', [])
        approve_applications_snapshot_display = convert_model_data_field_name_to_verbose_name(
            model=Application, data=approve_applications_snapshot
        )
        approve_system_users_snapshot = self.ticket.meta.get('approve_system_users_snapshot', [])
        approve_system_users_snapshot_display = convert_model_data_field_name_to_verbose_name(
            model=SystemUser, data=approve_system_users_snapshot
        )
        approve_date_start = self.ticket.meta.get('approve_date_start')
        approve_date_expired = self.ticket.meta.get('approve_date_expired')
        approved_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
        '''.format(
            __('Approved applications'), approve_applications_snapshot_display,
            __('Approved system users'), approve_system_users_snapshot_display,
            __('Approved date start'), approve_date_start,
            __('Approved date expired'), approve_date_expired
        )
        return approved_body

    def _create_application_permission(self):
        with tmp_to_root_org():
            application_permission = ApplicationPermission.objects.filter(id=self.ticket.id).first()
            if application_permission:
                return application_permission

        apply_category = self.ticket.meta.get('apply_category')
        apply_type = self.ticket.meta.get('apply_type')
        approved_applications_id = self.ticket.meta.get('approve_applications', [])
        approve_system_users_id = self.ticket.meta.get('approve_system_users', [])
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
                self.ticket.title, self.ticket.applicant_display,
                self.ticket.processor_display, str(self.ticket.id)
            )
        )
        permissions_data = {
            'id': self.ticket.id,
            'name': permission_name,
            'category': apply_category,
            'type': apply_type,
            'comment': permission_comment,
            'created_by': '{}:{}'.format(str(self.__class__.__name__), str(self.ticket.id)),
            'date_start': approve_date_start,
            'date_expired': approve_date_expired,
        }
        with tmp_to_org(self.ticket.org_id):
            application_permission = ApplicationPermission.objects.create(**permissions_data)
            application_permission.users.add(self.ticket.applicant)
            application_permission.applications.set(approved_applications_id)
            application_permission.system_users.set(approve_system_users_id)

        return application_permission
