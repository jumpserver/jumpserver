# -*- coding: utf-8 -*-
#
from urllib.parse import urljoin
from django.conf import settings
from django.utils.translation import ugettext as _

from common.utils import get_logger
from common.tasks import send_mail_async
from . import const

logger = get_logger(__file__)

EMAIL_TEMPLATE = '''
    <div>
        <p>
            {title} 
            <a href={ticket_detail_url}>
                <strong>{ticket_detail_url_description}</strong>
            </a>
        </p>
        <div>
            {body}
        </div>
    </div>
'''


def send_ticket_applied_mail_to_assignees(ticket):
    if not ticket.assignees:
        logger.debug("Not found assignees, ticket: {}({}), assignees: {}".format(
            ticket, str(ticket.id), ticket.assignees)
        )
        return

    ticket_detail_url = urljoin(settings.SITE_URL, const.TICKET_DETAIL_URL.format(id=str(ticket.id)))
    subject = _('New Ticket - {} ({})').format(ticket.title, ticket.get_type_display())
    message = EMAIL_TEMPLATE.format(
        title=_('Your has a new ticket, applicant - {}').format(str(ticket.applicant_display)),
        ticket_detail_url=ticket_detail_url,
        ticket_detail_url_description=_('click here to review'),
        body=ticket.body.replace('\n', '<br/>'),
    )
    if settings.DEBUG:
        logger.debug(message)
    recipient_list = [assignee.email for assignee in ticket.assignees.all()]
    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_ticket_processed_mail_to_applicant(ticket):
    if not ticket.applicant:
        logger.error("Not found applicant: {}({})".format(ticket.title, ticket.id))
        return

    ticket_detail_url = urljoin(settings.SITE_URL, const.TICKET_DETAIL_URL.format(id=str(ticket.id)))
    subject = _('Ticket has processed - {} ({})').format(ticket.title, ticket.processor_display)
    message = EMAIL_TEMPLATE.format(
        title=_('Your ticket has been processed, processor - {}').format(ticket.processor_display),
        ticket_detail_url=ticket_detail_url,
        ticket_detail_url_description=_('click here to review'),
        body=ticket.body.replace('\n', '<br/>'),
    )
    if settings.DEBUG:
        logger.debug(message)
    recipient_list = [ticket.applicant.email]
    send_mail_async.delay(subject, message, recipient_list, html_message=message)
