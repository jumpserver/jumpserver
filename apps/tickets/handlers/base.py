from django.utils.translation import ugettext as _

from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant,
    send_ticket_applied_mail_to_assignees
)
from tickets.const import StepState
from tickets.models import Ticket

logger = get_logger(__name__)


class BaseHandler:

    def __init__(self, ticket):
        self.ticket = ticket

    def on_state_change(self, state):
        self._on_comment_create(state)
        method = getattr(self, f'_on_{state}', lambda: None)
        return method()

    def _on_pending(self):
        self._send_applied_mail_to_assignees()

    def _on_approved(self):
        next_step = self.ticket.current_step.next()
        is_finished = not bool(next_step)
        if is_finished:
            self._send_processed_mail_to_applicant()
        else:
            self._send_processed_mail_to_applicant()
            self.ticket.approval_step += 1
            self._send_applied_mail_to_assignees()
        self.ticket.save()
        return is_finished

    def _on_rejected(self):
        self.__on_process()

    def _on_closed(self):
        self.__on_process()

    def __on_process(self):
        self._send_processed_mail_to_applicant()

    def on_step_state_change(self, state):
        pass

    def _on_step_pending(self, step):
        # Todo:
        pass

    def _on_step_rejected(self, step):
        # Todo:
        pass

    def _on_step_approved(self, step):
        pass

    def _send_applied_mail_to_assignees(self):
        assignees = self.ticket.current_assignees
        assignees_display = ', '.join([str(assignee) for assignee in assignees])
        logger.debug('Send applied email to assignees: {}'.format(assignees_display))
        send_ticket_applied_mail_to_assignees(self.ticket, assignees)

    def _send_processed_mail_to_applicant(self):
        logger.debug('Send processed mail to applicant: {}'.format(self.ticket.applicant))
        processor = self.ticket.processor
        send_ticket_processed_mail_to_applicant(self.ticket, processor)

    def _on_comment_create(self, state):
        user = self.ticket.processor
        # 打开或关闭工单，备注显示是自己，其他是受理人
        if state == StepState.pending or state == StepState.closed:
            user = self.ticket.applicant
        user_display = str(user)
        state_display = getattr(StepState, state).label
        data = {
            'body': _('{} {} the ticket').format(user_display, state_display),
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
        basic_body = self._construct_basic_body()
        meta_body = self._construct_meta_body()
        return basic_body + meta_body

    def _construct_basic_body(self):
        basic_body = '''
            {}: {}
            {}: {}
            {}: {}
            {}: {}
        '''.format(
            _('Ticket title'), self.ticket.title,
            _('Ticket type'), self.ticket.get_type_display(),
            _('Ticket status'), self.ticket.get_status_display(),
            _('Ticket applicant'), self.ticket.applicant,
        ).strip()
        body = self.body_html_format.format(_("Ticket basic info"), basic_body)
        return body

    def _construct_meta_body(self):
        body = ''
        open_body = self._base_construct_meta_body_of_open().strip()
        body += open_body
        return body

    def _base_construct_meta_body_of_open(self):
        meta_body_of_open = getattr(
            self, '_construct_meta_body_of_open', lambda: _('No content')
        )().strip()
        body = self.body_html_format.format(_('Ticket applied info'), meta_body_of_open)
        return body
