import textwrap
from django.utils.translation import ugettext as __


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
        if not self.is_approved:
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
        create_method()


class CreateCommentMixin:
    def create_comment(self, comment_body):
        comment_data = {
            'body': comment_body,
            'user': self.processor,
            'user_display': self.processor_display
        }
        return self.comments.create(**comment_data)

    def create_approved_comment(self):
        comment_body = self.construct_approved_body()
        # 页面展示需要取消缩进
        comment_body = textwrap.dedent(comment_body)
        self.create_comment(comment_body)

    def create_action_comment(self):
        comment_body = __(
            'User {} {} the ticket'.format(self.processor_display, self.get_action_display())
        )
        self.create_comment(comment_body)
