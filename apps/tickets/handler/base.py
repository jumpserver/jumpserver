import textwrap
from django.utils.translation import ugettext as __
from common.utils import get_logger
from tickets.utils import send_ticket_processed_mail_to_applicant


logger = get_logger(__name__)


class BaseHandler(object):

    def __init__(self, ticket):
        self.ticket = ticket

    # on action
    def on_open(self):
        self.ticket.applicant_display = str(self.ticket.applicant)
        meta_display = getattr(self, '_construct_meta_display_of_open', lambda: {})()
        self.ticket.meta.update(meta_display)
        self.ticket.save()
        self._create_comment_on_action()
        self._create_comment_on_open()

    def on_approve(self):
        meta_display = getattr(self, '_construct_meta_display_of_approve', lambda: {})()
        self.ticket.meta.update(meta_display)
        self._on_process()
        self._create_comment_on_approve()

    def on_reject(self):
        self._on_process()

    def on_close(self):
        self._on_process()

    def _on_process(self):
        self.ticket.processor_display = str(self.ticket.processor)
        self.ticket.set_status_closed()
        self.ticket.save()
        self._create_comment_on_action()
        self._send_processed_mail_to_applicant()

    def dispatch(self, action):
        method = getattr(self, f'on_{action}', lambda: None)
        return method()

    # email

    def _send_processed_mail_to_applicant(self):
        msg = 'Ticket ({}) has processed, send mail to applicant ({})'.format(
            self.ticket.title, self.ticket.applicant_display
        )
        logger.debug(msg)
        send_ticket_processed_mail_to_applicant(self.ticket)

    # comments

    def _create_comment_on_open(self):
        body = self._base_construct_meta_body_of_open()
        comment_data = {
            'body': textwrap.dedent(body),
            'user': self.ticket.applicant,
            'user_display': self.ticket.applicant_display
        }
        self._create_comment(comment_data)

    def _create_comment_on_approve(self):
        body = self._base_construct_meta_body_of_approve()
        comment_data = {
            'body': textwrap.dedent(body),
            'user': self.ticket.applicant,
            'user_display': self.ticket.applicant_display
        }
        self._create_comment(comment_data)

    def _create_comment_on_action(self):
        user = self.ticket.applicant if self.ticket.action_open else self.ticket.processor
        user_display = str(user)
        action_display = self.ticket.get_action_display()
        comment_data = {
            'body': __('User {} {} the ticket'.format(user_display, action_display)),
            'user': user,
            'user_display': user_display
        }
        self._create_comment(comment_data)

    def _create_comment(self, data):
        return self.ticket.comments.create(**data)

    # body

    def get_body(self):
        old_body = self.ticket.meta.get('body')
        if old_body:
            # 之前版本的body
            return old_body
        basic_body = self._construct_basic_body()
        meta_body = self._construct_meta_body()
        return basic_body + meta_body

    def _construct_basic_body(self):
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
            __('Ticket title'), self.ticket.title,
            __('Ticket type'), self.ticket.get_type_display(),
            __('Ticket applicant'), self.ticket.applicant_display,
            __('Ticket assignees'), self.ticket.assignees_display,
            __('Ticket processor'), self.ticket.processor_display,
            __('Ticket action'), self.ticket.get_action_display(),
            __('Ticket status'), self.ticket.get_status_display()
        )
        return basic_body

    def _construct_meta_body(self):
        body = ''
        open_body = self._base_construct_meta_body_of_open()
        body += open_body
        if self.ticket.action_approve:
            approve_body = self._base_construct_meta_body_of_approve()
            body += approve_body
        return body

    def _base_construct_meta_body_of_open(self):
        open_body = '''
            {}:
            {}
        '''.format(
            __('Ticket applied info'),
            getattr(self, '_construct_meta_body_of_open', lambda: 'No')()
        )
        return open_body

    def _base_construct_meta_body_of_approve(self):
        approve_body = '''
            {}:
            {}
        '''.format(
            __('Ticket approved info'),
            getattr(self, '_construct_meta_body_of_approve', lambda: 'No')()
        )
        return approve_body
