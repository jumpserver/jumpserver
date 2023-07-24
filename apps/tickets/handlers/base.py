import html2text
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from common.utils import get_logger
from tickets.const import TicketState, TicketType
from tickets.utils import (
    send_ticket_processed_mail_to_applicant,
    send_ticket_applied_mail_to_assignees
)

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

    def _diff_prev_approve_context(self, state):
        diff_context = {}
        if state != TicketState.approved:
            return diff_context

        if self.ticket.type != TicketType.apply_asset:
            return diff_context

        # 企业微信，钉钉审批不做diff
        if not hasattr(self.ticket, 'old_rel_snapshot'):
            return diff_context

        old_rel_snapshot = self.ticket.old_rel_snapshot
        current_rel_snapshot = self.ticket.get_local_snapshot()
        diff = set(current_rel_snapshot.items()) - set(old_rel_snapshot.items())
        if not diff:
            return diff_context

        content = []
        for k, v in sorted(list(diff), reverse=True):
            content.append([k, old_rel_snapshot[k], v])
        headers = [_('Change field'), _('Before change'), _('After change')]
        return {'headers': headers, 'content': content}

    def _create_state_change_comment(self, state):
        # 打开或关闭工单，备注显示是自己，其他是受理人
        if state in [TicketState.reopen, TicketState.pending, TicketState.closed]:
            user = self.ticket.applicant
        else:
            user = self.ticket.processor

        user_display = str(user)
        state_display = getattr(TicketState, state).label
        approve_info = _('{} {} the ticket').format(user_display, state_display)
        context = self._diff_prev_approve_context(state)
        context.update({'approve_info': approve_info})
        body = self.safe_html_script(
            render_to_string('tickets/ticket_approve_diff.html', context)
        )
        data = {
            'body': body,
            'user': user,
            'user_display': str(user),
            'type': 'state',
            'state': state
        }
        return self.ticket.comments.create(**data)

    @staticmethod
    def safe_html_script(unsafe_html):
        unsafe_html = unsafe_html.replace('\n', '')
        html_str = html2text.html2text(unsafe_html)
        return html_str
