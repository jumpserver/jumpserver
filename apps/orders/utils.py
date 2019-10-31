# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import ugettext as _

from common.utils import get_logger, reverse
from common.tasks import send_mail_async

logger = get_logger(__name__)


def send_login_confirm_order_mail_to_assignees(order, assignees):
    recipient_list = [user.email for user in assignees]
    user = order.user
    if not recipient_list:
        logger.error("Order not has assignees: {}".format(order.id))
        return
    subject = '{}: {}'.format(_("New order"), order.title)
    detail_url = reverse('orders:login-confirm-order-detail',
                         kwargs={'pk': order.id}, external=True)
    message = _("""
        <div>
            <p>Your has a new order</p>
            <div>
                <b>Title:</b> {order.title}
                <br/>
                <b>User:</b> {user}
                <br/>
                <b>Assignees:</b> {order.assignees_display}
                <br/>
                <b>City:</b> {order.city}
                <br/>
                <b>IP:</b> {order.ip}
                <br/>
                <a href={url}>click here to review</a> 
            </div>
        </div>
    """).format(order=order, user=user, url=detail_url)
    send_mail_async.delay(subject, message, recipient_list, html_message=message)


def send_login_confirm_action_mail_to_user(order):
    if not order.user:
        logger.error("Order not has user: {}".format(order.id))
        return
    user = order.user
    recipient_list = [user.email]
    subject = '{}: {}'.format(_("Order has been reply"), order.title)
    message = _("""
        <div>
            <p>Your order has been replay</p>
            <div>
                <b>Title:</b> {order.title}
                <br/>
                <b>Assignee:</b> {order.assignee_display}
                <br/>
                <b>Status:</b> {order.status_display}
                <br/>
            </div>
        </div>
     """).format(order=order)
    send_mail_async.delay(subject, message, recipient_list, html_message=message)
