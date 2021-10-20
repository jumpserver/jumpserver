from urllib.parse import urljoin

from django.conf import settings
from django.utils.translation import ugettext as _

from . import const
from notifications.notifications import UserMessage
from common.utils import get_logger
from .models import Ticket

logger = get_logger(__file__)

EMAIL_TEMPLATE = '''
    <div>
        <p>
            {title} 
        </p>
        <div>
            {body}
        </div>
        <div>
            <a href={ticket_detail_url}>
                <strong>{ticket_detail_url_description}</strong>
            </a>
        </div>
    </div>
'''


class BaseTicketMessage(UserMessage):
    title: ''
    ticket: Ticket
    content_title: str

    @property
    def subject(self):
        return self.title.format(self.ticket.title, self.ticket.get_type_display())

    @property
    def ticket_detail_url(self):
        return urljoin(settings.SITE_URL, const.TICKET_DETAIL_URL.format(id=str(self.ticket.id)))

    def get_html_msg(self) -> dict:
        message = EMAIL_TEMPLATE.format(
            title=self.content_title,
            ticket_detail_url=self.ticket_detail_url,
            ticket_detail_url_description=_('click here to review'),
            body=self.ticket.body.replace('\n', '<br/>'),
        )
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        return cls(None)


class TicketAppliedToAssignee(BaseTicketMessage):
    title = _('New Ticket - {} ({})')

    def __init__(self, user, ticket):
        self.ticket = ticket
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your has a new ticket, applicant - {}').format(str(self.ticket.applicant_display))


class TicketProcessedToApplicant(BaseTicketMessage):
    title = _('Ticket has processed - {} ({})')

    def __init__(self, user, ticket, processor):
        self.ticket = ticket
        self.processor = processor
        super().__init__(user)

    @property
    def content_title(self):
        return _('Your ticket has been processed, processor - {}').format(str(self.processor))
