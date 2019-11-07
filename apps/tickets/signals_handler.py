# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_save

from common.utils import get_logger
from .models import LoginConfirmTicket
from .utils import (
    send_login_confirm_ticket_mail_to_assignees,
    send_login_confirm_action_mail_to_user
)


logger = get_logger(__name__)


@receiver(m2m_changed, sender=LoginConfirmTicket.assignees.through)
def on_login_confirm_ticket_assignees_set(sender, instance=None, action=None,
                                        model=None, pk_set=None, **kwargs):
    if action == 'post_add':
        logger.debug('New ticket create, send mail: {}'.format(instance.id))
        assignees = model.objects.filter(pk__in=pk_set)
        send_login_confirm_ticket_mail_to_assignees(instance, assignees)


@receiver(post_save, sender=LoginConfirmTicket)
def on_login_confirm_ticket_status_change(sender, instance=None, created=False, **kwargs):
    if created or instance.status == "pending":
        return
    logger.debug('Ticket changed, send mail: {}'.format(instance.id))
    send_login_confirm_action_mail_to_user(instance)
