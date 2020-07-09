# -*- coding: utf-8 -*-
#
from urllib.parse import urljoin
from django.conf import settings
from django.utils.translation import ugettext as _

from common.utils import get_logger
from common.tasks import send_mail_async

logger = get_logger(__name__)
from tickets.models import Ticket


def send_new_ticket_mail_to_assignees(ticket: Ticket, assignees):
    recipient_list = [user.email for user in assignees]
    user = ticket.user
    if not recipient_list:
        logger.error("Ticket not has assignees: {}".format(ticket.id))
        return
    subject = '{}: {}'.format(_("New ticket"), ticket.title)

    # 这里要设置前端地址，因为要直接跳转到页面
    if ticket.type == ticket.TYPE_REQUEST_ASSET_PERM:
        detail_url = urljoin(settings.SITE_URL, f'/tickets/tickets/request-asset-perm/{ticket.id}')
    else:
        detail_url = urljoin(settings.SITE_URL, f'/tickets/tickets/{ticket.id}')

    message = _("""
        <div>
            <p>Your has a new ticket</p>
            <div>
                {body}
                <br/>
                <a href={url}>click here to review</a> 
            </div>
        </div>
    """).format(body=ticket.body, user=user, url=detail_url)
    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_ticket_action_mail_to_user(ticket):
    if not ticket.user:
        logger.error("Ticket not has user: {}".format(ticket.id))
        return
    user = ticket.user
    recipient_list = [user.email]
    subject = '{}: {}'.format(_("Ticket has been reply"), ticket.title)
    message = _("""
        <div>
            <p>Your ticket has been replay</p>
            <div>
                <b>Title:</b> {ticket.title}
                <br/>
                <b>Assignee:</b> {ticket.assignee_display}
                <br/>
                <b>Status:</b> {ticket.status_display}
                <br/>
            </div>
        </div>
     """).format(ticket=ticket)
    send_mail_async.delay(subject, message, recipient_list, html_message=message)
