from django.utils.translation import ugettext as _
from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant, send_ticket_applied_mail_to_assignees
)
from tickets.const import TicketAction

logger = get_logger(__name__)


class BaseHandler(object):

    def __init__(self, ticket):
        self.ticket = ticket

    # on action
    def _on_open(self):
        self.ticket.applicant_display = str(self.ticket.applicant)
        meta_display = getattr(self, '_construct_meta_display_of_open', lambda: {})()
        self.ticket.meta.update(meta_display)
        self.ticket.save()
        self._send_applied_mail_to_assignees()

    def _on_approve(self):
        is_finish = False
        if self.ticket.approval_step != len(self.ticket.process_map):
            self.ticket.approval_step += 1
            self.ticket.create_related_node()
        else:
            self.ticket.set_state_approve()
            self.ticket.set_status_closed()
            is_finish = True
        self._send_applied_mail_to_assignees()

        self.__on_process(self.ticket.processor)
        return is_finish

    def _on_reject(self):
        self.ticket.set_state_reject()
        self.ticket.set_status_closed()
        self.__on_process(self.ticket.processor)

    def _on_close(self):
        self.ticket.set_state_closed()
        self.ticket.set_status_closed()
        self.__on_process(self.ticket.processor)

    def __on_process(self, processor):
        self._send_processed_mail_to_applicant(processor)
        self.ticket.save()

    def dispatch(self, action):
        processor = self.ticket.processor
        current_node = self.ticket.current_node.first()
        self.ticket.process_map[self.ticket.approval_step - 1].update({
            'approval_date': str(current_node.date_updated),
            'state': current_node.state,
            'processor': processor.id if processor else '',
            'processor_display': str(processor) if processor else '',
        })
        self.ticket.save()
        self._create_comment_on_action(action)
        method = getattr(self, f'_on_{action}', lambda: None)
        return method()

    # email
    def _send_applied_mail_to_assignees(self):
        logger.debug('Send applied email to assignees: {}'.format(
            ', '.join([str(i.assignee) for i in self.ticket.current_node.first().ticket_assignees.all()])))
        send_ticket_applied_mail_to_assignees(self.ticket)

    def _send_processed_mail_to_applicant(self, processor):
        logger.debug('Send processed mail to applicant: {}'.format(self.ticket.applicant_display))
        send_ticket_processed_mail_to_applicant(self.ticket, processor)

    # comments
    def _create_comment_on_action(self, action):
        user = self.ticket.applicant if self.ticket.state_open or self.ticket.state_close else self.ticket.processor
        user_display = str(user)
        action_display = getattr(TicketAction, action).label
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
        '''.format(
            _('Ticket title'), self.ticket.title,
            _('Ticket type'), self.ticket.get_type_display(),
            _('Ticket status'), self.ticket.get_status_display(),
            _('Ticket applicant'), self.ticket.applicant_display,
        )
        body = self.body_html_format.format(_("Ticket basic info"), basic_body)
        return body

    def _construct_meta_body(self):
        body = ''
        open_body = self._base_construct_meta_body_of_open()
        body += open_body
        return body

    def _base_construct_meta_body_of_open(self):
        meta_body_of_open = getattr(
            self, '_construct_meta_body_of_open', lambda: _('No content')
        )()
        body = self.body_html_format.format(_('Ticket applied info'), meta_body_of_open)
        return body
