# -*- coding: utf-8 -*-
#
from urllib.parse import urljoin
from django.conf import settings
from django.utils.translation import ugettext as _

from common.const.front_urls import TICKET_DETAIL
from common.utils import get_logger
from common.tasks import send_mail_async
from tickets.models import Ticket

logger = get_logger(__name__)


def send_ticket_applied_mail_to_assignees(ticket: Ticket, assignees):
    if not assignees:
        logger.error("Ticket not has assignees: {}".format(ticket.id))
        return

    subject = '{}: {}'.format(_("New ticket"), ticket.title)
    recipient_list = [assignee.email for assignee in assignees]
    # 这里要设置前端地址，因为要直接跳转到页面
    detail_url = urljoin(settings.SITE_URL, TICKET_DETAIL.format(id=ticket.id))
    message = _(
        """<div>
            <p>Your has a new ticket</p>
            <div>
                <b>Ticket:</b> 
                <br/>
                {body}
                <br/>
                <a href={url}>click here to review</a> 
            </div>
        </div>
        """.format(
            body=ticket.body,
            url=detail_url
        )
    )
    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_ticket_processed_mail_to_applicant(ticket):
    if not ticket.applicant:
        logger.error("Ticket not has applicant: {}".format(ticket.id))
        return
    applicant = ticket.applicant
    recipient_list = [applicant.email]
    subject = '{} ({})'.format(_("Ticket has processed"), ticket.title)
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
    send_mail_async.delay(subject, message, recipient_list, html_message=message)
