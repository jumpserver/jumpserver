from django.utils.translation import ugettext as _
from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant, send_ticket_applied_mail_to_assignees
)


logger = get_logger(__name__)


class BaseHandler(object):

    def __init__(self, ticket):
        self.ticket = ticket

    # on action
    def _on_open(self):
        self.ticket.applicant_display = str(self.ticket.applicant)
        self.ticket.assignees_display = [str(assignee) for assignee in self.ticket.assignees.all()]
        meta_display = getattr(self, '_construct_meta_display_of_open', lambda: {})()
        self.ticket.meta.update(meta_display)
        self.ticket.save()
        self._send_applied_mail_to_assignees()

    def _on_approve(self):
        meta_display = getattr(self, '_construct_meta_display_of_approve', lambda: {})()
        self.ticket.meta.update(meta_display)
        self.__on_process()

    def _on_reject(self):
        self.__on_process()

    def _on_close(self):
        self.__on_process()

    def __on_process(self):
        self.ticket.processor_display = str(self.ticket.processor)
        self.ticket.set_status_closed()
        self._send_processed_mail_to_applicant()
        self.ticket.save()

    def dispatch(self, action):
        self._create_comment_on_action()
        method = getattr(self, f'_on_{action}', lambda: None)
        return method()

    # email
    def _send_applied_mail_to_assignees(self):
        logger.debug('Send applied email to assignees: {}'.format(self.ticket.assignees_display))
        send_ticket_applied_mail_to_assignees(self.ticket)

    def _send_processed_mail_to_applicant(self):
        logger.debug('Send processed mail to applicant: {}'.format(self.ticket.applicant_display))
        send_ticket_processed_mail_to_applicant(self.ticket)

    # comments
    def _create_comment_on_action(self):
        user = self.ticket.applicant if self.ticket.action_open else self.ticket.processor
        user_display = str(user)
        action_display = self.ticket.get_action_display()
        data = {
            'body': _('{} {} the ticket').format(user_display, action_display),
            'user': user,
            'user_display': user_display
        }
        return self.ticket.comments.create(**data)

    # body
    body_html_format = '''
        {}:
        <div style="margin-left: 20px;">{}</div>
    '''

    def get_body(self):
        old_body = self.ticket.meta.get('body')
        if old_body:
            # 之前版本的body
            return old_body
        basic_body = self._construct_basic_body()
        meta_body = self._construct_meta_body()
        return basic_body + meta_body

    def _construct_basic_body(self):
        basic_body = '''{}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {},
            {}: {}
        '''.format(
            _('Ticket title'), self.ticket.title,
            _('Ticket type'), self.ticket.get_type_display(),
            _('Ticket status'), self.ticket.get_status_display(),
            _('Ticket action'), self.ticket.get_action_display(),
            _('Ticket applicant'), self.ticket.applicant_display,
            _('Ticket assignees'), self.ticket.assignees_display,
        )
        if self.ticket.status_closed:
            basic_body += '''{}: {}'''.format(_('Ticket processor'), self.ticket.processor_display)
        body = self.body_html_format.format(_("Ticket basic info"), basic_body)
        return body

    def _construct_meta_body(self):
        body = ''
        open_body = self._base_construct_meta_body_of_open()
        body += open_body
        if self.ticket.action_approve:
            approve_body = self._base_construct_meta_body_of_approve()
            body += approve_body
        return body

    def _base_construct_meta_body_of_open(self):
        meta_body_of_open = getattr(self, '_construct_meta_body_of_open', lambda: 'No')()
        body = self.body_html_format.format(_('Ticket applied info'), meta_body_of_open)
        return body

    def _base_construct_meta_body_of_approve(self):
        meta_body_of_approve = getattr(self, '_construct_meta_body_of_approve', lambda: 'No')()
        body = self.body_html_format.format(_('Ticket approved info'), meta_body_of_approve)
        return body
