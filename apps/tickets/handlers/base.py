from django.utils.translation import ugettext as _

from common.utils import get_logger
from tickets.utils import (
    send_ticket_processed_mail_to_applicant,
    send_ticket_applied_mail_to_assignees
)
from tickets.const import TicketState, TicketType

logger = get_logger(__name__)


class BaseHandler:

    def __init__(self, ticket):
        self.ticket = ticket

    def on_change_state(self, state):
        self._create_state_change_comment(state)
        handler = getattr(self, f'_on_{state}', lambda: None)
        return handler()

    def _on_pending(self):
        self._send_applied_mail_to_assignees()

    def on_step_state_change(self, step, state):
        self._create_state_change_comment(state)
        handler = getattr(self, f'_on_step_{state}', lambda: None)
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

    def _on_step_closed(self, step):
        self._send_processed_mail_to_applicant()

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
        processor = step.processor if step else applicant
        logger.debug('Send processed mail to applicant: {}'.format(applicant))
        send_ticket_processed_mail_to_applicant(self.ticket, processor)

    def _diff_prev_approve_info(self, state):
        diff_info = ''
        if state != TicketState.approved:
            return diff_info
        if self.ticket.type not in [TicketType.apply_asset, TicketType.apply_application]:
            return diff_info

        old_rel_snapshot = self.ticket.old_rel_snapshot
        current_rel_snapshot = self.ticket.get_local_snapshot()
        diff = set(current_rel_snapshot.items()) - set(old_rel_snapshot.items())
        if not diff:
            return diff_info

        diff_info += '对审批信息作出如下修改:\n'
        for k, v in sorted(list(diff), reverse=True):
            diff_info += f'    {k}: {old_rel_snapshot[k]} ==> {v}\n'
        return diff_info

    def _create_state_change_comment(self, state):
        # 打开或关闭工单，备注显示是自己，其他是受理人
        if state in [TicketState.reopen, TicketState.pending, TicketState.closed]:
            user = self.ticket.applicant
        else:
            user = self.ticket.processor

        user_display = str(user)
        state_display = getattr(TicketState, state).label
        base_info = _('{} {} the ticket').format(user_display, state_display)
        diff_info = self._diff_prev_approve_info(state)
        data = {
            'body': f'{base_info}\n{diff_info}',
            'user': user,
            'user_display': str(user),
            'type': 'state',
            'state': state
        }
        return self.ticket.comments.create(**data)
