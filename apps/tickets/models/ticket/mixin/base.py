import textwrap
from django.utils.translation import ugettext as __


class SetDisplayFieldMixin:

    def set_applicant_display(self):
        if self.has_applied:
            self.applicant_display = str(self.applicant)

    def set_assignees_display(self):
        if self.has_applied:
            self.assignees_display = [str(assignee) for assignee in self.assignees.all()]

    def set_processor_display(self):
        if self.has_processed:
            self.processor_display = str(self.processor)

    def set_meta_display(self):
        method_name = f'construct_meta_{self.type}_{self.action}_fields_display'
        meta_display = getattr(self, method_name, lambda: {})()
        self.meta.update(meta_display)

    def set_display_fields(self):
        self.set_applicant_display()
        self.set_processor_display()
        self.set_meta_display()


class ConstructBodyMixin:
    # applied body
    def construct_applied_body(self):
        construct_method = getattr(self, f'construct_{self.type}_applied_body', lambda: 'No')
        applied_body = construct_method()
        body = '''
            {}:
            {}
        '''.format(
            __('Ticket applied info'),
            applied_body
        )
        return body

    # approved body
    def construct_approved_body(self):
        construct_method = getattr(self, f'construct_{self.type}_approved_body', lambda: 'No')
        approved_body = construct_method()
        body = '''
            {}:
            {}
        '''.format(
            __('Ticket approved info'),
            approved_body
        )
        return body

    # meta body
    def construct_meta_body(self):
        applied_body = self.construct_applied_body()
        if not self.action_approve:
            return applied_body
        approved_body = self.construct_approved_body()
        return applied_body + approved_body

    # basic body
    def construct_basic_body(self):
        basic_body = '''
            {}:
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            __("Ticket basic info"),
            __('Ticket title'), self.title,
            __('Ticket type'), self.get_type_display(),
            __('Ticket applicant'), self.applicant_display,
            __('Ticket assignees'), self.assignees_display,
            __('Ticket processor'), self.processor_display,
            __('Ticket action'), self.get_action_display(),
            __('Ticket status'), self.get_status_display()
        )
        return basic_body

    @property
    def body(self):
        old_body = self.meta.get('body')
        if old_body:
            # 之前版本的body
            return old_body
        basic_body = self.construct_basic_body()
        meta_body = self.construct_meta_body()
        return basic_body + meta_body


class CreatePermissionMixin:
    # create permission
    def create_permission(self):
        create_method = getattr(self, f'create_{self.type}_permission', lambda: None)
        permission = create_method()
        return permission


class CreateCommentMixin:
    def create_comment(self, comment_body):
        # 页面展示需要取消缩进
        comment_body = textwrap.dedent(comment_body)
        comment_data = {
            'body': comment_body,
            'user': self.processor,
            'user_display': self.processor_display
        }
        return self.comments.create(**comment_data)

    def create_applied_comment(self):
        comment_body = self.construct_applied_body()
        self.create_comment(comment_body)

    def create_approved_comment(self):
        comment_body = self.construct_approved_body()
        self.create_comment(comment_body)

    def create_action_comment(self):
        if self.has_applied:
            user_display = self.applicant_display
        if self.has_processed:
            user_display = self.processor_display
        comment_body = __(
            'User {} {} the ticket'.format(user_display, self.get_action_display())
        )
        self.create_comment(comment_body)
