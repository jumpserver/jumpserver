# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from django.conf import settings

from common.tasks import send_mail_async
from common.utils import get_logger, reverse
from .models import LoginConfirmOrder

logger = get_logger(__name__)


def send_mail(order, assignees):
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
                <b>City:</b> {order.city}
                <br/>
                <b>IP:</b> {order.ip}
                <br/>
                <a href={url}>click here to review</a> 
            </div>
        </div>
    """).format(order=order, user=user, url=detail_url)
    if settings.DEBUG:
        try:
            print(message)
        except OSError:
            pass

    send_mail_async.delay(subject, message, recipient_list, html_message=message)


@receiver(m2m_changed, sender=LoginConfirmOrder.assignees.through)
def on_login_confirm_order_assignee_set(sender, instance=None, action=None,
                                        model=None, pk_set=None, **kwargs):
    print(">>>>>>>>>>>>>>>>>>>>>>>.")
    print(action)
    if action == 'post_add':
        print("<<<<<<<<<<<<<<<<<<<<")
        logger.debug('New order create, send mail: {}'.format(instance.id))
        assignees = model.objects.filter(pk__in=pk_set)
        send_mail(instance, assignees)

