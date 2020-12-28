# -*- coding: utf-8 -*-
#
from urllib.parse import urljoin
from django.conf import settings
from django.utils.translation import ugettext as _

from common.utils import get_logger
from common.tasks import send_mail_async
from . import const

logger = get_logger(__name__)


def send_ticket_applied_mail_to_assignees(ticket, assignees):
    if not assignees:
        logger.debug("Not found assignees, ticket: {}({}), assignees: {}".format(
            ticket, str(ticket.id), assignees)
        )
        return

    subject = _('New Ticket: {} ({})'.format(ticket.title, ticket.get_type_display()))
    ticket_detail_url = urljoin(
        settings.SITE_URL, const.TICKET_DETAIL_URL.format(id=str(ticket.id))
    )
    message = _(
        """<div>
            <p>Your has a new ticket</p>
            <div>
                <b>Ticket:</b> 
                <br/>
                {body}
                <br/>
                <a href={ticket_detail_url}>click here to review</a> 
            </div>
        </div>
        """.format(
            body=ticket.body,
            ticket_detail_url=ticket_detail_url
        )
    )
    recipient_list = [assignee.email for assignee in assignees]
    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_ticket_processed_mail_to_applicant(ticket):
    if not ticket.applicant:
        logger.error("Not found applicant: {}({})".format(ticket.title, ticket.id))
        return
    subject = _('Ticket has processed: {} ({})').format(ticket.title, ticket.get_type_display())
    message = _(
        """
        <div>
            <p>Your ticket has been processed</p>
            <div>
                <b>Ticket:</b> 
                <br/>
                {body}
                <br/>
            </div>
        </div>
        """.format(
            body=ticket.body,
        )
    )
    recipient_list = [ticket.applicant.email]
    send_mail_async.delay(subject, message, recipient_list, html_message=message)
