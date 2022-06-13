from django.utils.translation import ugettext as _

from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant,
    send_ticket_applied_mail_to_assignees
)
from tickets.const import TicketState, TicketStatus

logger = get_logger(__name__)


class BaseHandler:

    def __init__(self, ticket):
        self.ticket = ticket

    def on_change_state(self, state):
        self._create_state_change_comment(state)
        handler = getattr(self, f'_on_{state}', lambda: None)
        return handler()

    def _on_approved(self):
        self._send_processed_mail_to_applicant()

    def _on_closed(self):
        self._send_processed_mail_to_applicant()

    def on_step_state_change(self, step, state):
        self._create_state_change_comment(state)
        handler = getattr(self, f'_on_step_{state}', lambda x, y: None)
        return handler(step)

    def _on_step_approved(self, step):
        next_step = step.next()
        is_finished = not next_step
        if is_finished:
            self._send_processed_mail_to_applicant(step)
        else:
            self._send_processed_mail_to_applicant(step)
            self._send_applied_mail_to_assignees(next_step)
        return is_finished

    def _on_step_rejected(self, step):
        self._send_processed_mail_to_applicant(step)

    def _send_applied_mail_to_assignees(self, step=None):
        if step:
            assignees = [step.assignee for step in step.ticket_assignees.all()]
        else:
            assignees = self.ticket.current_assignees
        assignees_display = ', '.join([str(assignee) for assignee in assignees])
        logger.debug('Send applied email to assignees: {}'.format(assignees_display))
        send_ticket_applied_mail_to_assignees(self.ticket, assignees)

    def _send_processed_mail_to_applicant(self, step=None):
        applicant = self.ticket.applicant
        if self.ticket.status == TicketStatus.closed:
            processor = applicant
        else:
            processor = step.processor if step else self.ticket.processor
        logger.debug('Send processed mail to applicant: {}'.format(applicant))
        send_ticket_processed_mail_to_applicant(self.ticket, processor)

    def _create_state_change_comment(self, state):
        # 打开或关闭工单，备注显示是自己，其他是受理人
        if state == TicketState.reopen or state == TicketState.closed:
            user = self.ticket.applicant
        else:
            user = self.ticket.processor

        data = {
            'user': user,
            'user_display': str(user),
            'type': 'status',
            'status': state,
            'ticket': self.ticket
        }
        return self.ticket.comments.create(**data)
