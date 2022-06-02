from django.utils.translation import ugettext as _

from common.utils import get_logger
from users.models import User
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

    def _on_pending(self):
        self._send_applied_mail_to_assignees()

    def _on_approved(self):
        if self.ticket.approval_step != len(self.ticket.process_map):
            self._send_processed_mail_to_applicant()
            self.ticket.approval_step += 1
            self._send_applied_mail_to_assignees()
            is_finished = False
        else:
            self.ticket.set_state(Ticket.State.approved)
            self.ticket.set_status(Ticket.Status.closed)
            self._send_processed_mail_to_applicant()
            is_finished = True

        self.ticket.save()
        return is_finished

    def _on_rejected(self):
        self.ticket.set_state(Ticket.State.rejected)
        self.ticket.set_status(Ticket.Status.closed)
        self.__on_process()

    def _on_closed(self):
        self.ticket.set_state(Ticket.State.closed)
        self.ticket.set_status(Ticket.Status.closed)
        self.__on_process()

    def __on_process(self):
        self._send_processed_mail_to_applicant()
        self.ticket.save()

    def dispatch(self, state):
        processor = self.ticket.processor
        current_step = self.ticket.current_step
        self.ticket.process_map[self.ticket.approval_step - 1].update({
            'approval_date': str(current_step.date_updated),
            'state': current_step.state,
            'processor': processor.id if processor else '',
            'processor_display': str(processor) if processor else '',
        })
        self.ticket.save()
        self._create_comment_on_state(state)
        method = getattr(self, f'_on_{state}', lambda: None)
        return method()

    # email
    def _send_applied_mail_to_assignees(self):
        current_process = self.ticket.process_map[self.ticket.approval_step - 1]
        assignees_display = current_process['assignees_display']
        logger.debug('Send applied email to assignees: {}'.format(assignees_display))
        assignees = User.objects.filter(id__in=current_process['assignees'])
        send_ticket_applied_mail_to_assignees(self.ticket, assignees)

    def _send_processed_mail_to_applicant(self):
        logger.debug('Send processed mail to applicant: {}'.format(self.ticket.applicant))
        processor = self.ticket.processor
        send_ticket_processed_mail_to_applicant(self.ticket, processor)

    def _create_comment_on_state(self, state):
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
        old_body = self.ticket.meta.get('body')
        if old_body:
            # 之前版本的body
            return old_body
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
