from django.utils.translation import ugettext as _

from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant,
    send_ticket_applied_mail_to_assignees
)
from tickets.const import StepState, TicketState

logger = get_logger(__name__)


class BaseHandler:

    def __init__(self, ticket):
        self.ticket = ticket

    def on_state_change(self, state):
        self._create_state_change_comment(state)
        method = getattr(self, f'_on_{state}', lambda: None)
        return method()

    def _on_approved(self):
        pass

    def _on_rejected(self):
        self._send_processed_mail_to_applicant()

    def _on_closed(self):
        pass

    def on_step_state_change(self, state):
        handler = getattr(self, f'_on_step_{state}', lambda: None)
        handler()

    def _on_step_pending(self, step):
        pass

    def _on_step_rejected(self, step):
        pass

    def _on_step_active(self, step):
        self._send_applied_mail_to_assignees(step)

    def _on_step_approved(self, step):
        pass

    def _send_applied_mail_to_assignees(self, step):
        assignees = [a.assignee for a in step.ticket_assignees.all()]
        assignees_display = ', '.join([str(assignee) for assignee in assignees])
        logger.debug('Send applied email to assignees: {}'.format(assignees_display))
        send_ticket_applied_mail_to_assignees(self.ticket, assignees)

    def _send_processed_mail_to_applicant(self):
        logger.debug('Send processed mail to applicant: {}'.format(self.ticket.applicant))
        processor = self.ticket.processor
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

    def _basic_items(self):
        items = [
            (_('Title'), self.ticket.title),
            (_('Type'), self.ticket.get_type_display()),
            (_('Status'), self.ticket.get_status_display()),
            (_('Applicant'), self.ticket.applicant)
        ]
        return items

    def _spec_items(self) -> list:
        raise NotImplemented()
