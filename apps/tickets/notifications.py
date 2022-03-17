from urllib.parse import urljoin

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from . import const
from notifications.notifications import UserMessage
from common.utils import get_logger
from .models import Ticket

logger = get_logger(__file__)


class BaseTicketMessage(UserMessage):
    title: ''
    ticket: Ticket
    content_title: str

    @property
    def ticket_detail_url(self):
        tp = self.ticket.type
        return urljoin(
            settings.SITE_URL,
            const.TICKET_DETAIL_URL.format(
                id=str(self.ticket.id),
                type=tp
            )
        )

    @property
    def content_title(self):
        raise NotImplementedError

    @property
    def subject(self):
        raise NotImplementedError

    def get_html_msg(self) -> dict:
        context = dict(
            title=self.content_title,
            ticket_detail_url=self.ticket_detail_url,
            body=self.ticket.body.replace('\n', '<br/>'),
        )
        message = render_to_string('tickets/_msg_ticket.html', context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        return None


class TicketAppliedToAssignee(BaseTicketMessage):
    def __init__(self, user, ticket):
        self.ticket = ticket
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your has a new ticket, applicant - {}').format(
            str(self.ticket.applicant_display)
        )

    @property
    def subject(self):
        title = _('New Ticket - {} ({})').format(
            self.ticket.title, self.ticket.get_type_display()
        )
        return title

    @classmethod
    def gen_test_msg(cls):
        from .models import Ticket
        from users.models import User
        ticket = Ticket.objects.first()
        user = User.objects.first()
        return cls(user, ticket)


class TicketProcessedToApplicant(BaseTicketMessage):
    def __init__(self, user, ticket, processor):
        self.ticket = ticket
        self.processor = processor
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your ticket has been processed, processor - {}').format(str(self.processor))

    @property
    def subject(self):
        title = _('Ticket has processed - {} ({})').format(
            self.ticket.title, self.ticket.get_type_display()
        )
        return title

    @classmethod
    def gen_test_msg(cls):
        from .models import Ticket
        from users.models import User
        ticket = Ticket.objects.first()
        user = User.objects.first()
        processor = User.objects.last()
        return cls(user, ticket, processor)
