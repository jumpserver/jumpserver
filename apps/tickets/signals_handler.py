# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_save, pre_save

from common.utils import get_logger
from .models import Ticket, Comment
from .utils import (
    send_new_ticket_mail_to_assignees,
    send_ticket_action_mail_to_user
)


logger = get_logger(__name__)


@receiver(post_save, sender=Ticket)
def on_ticket_approved(sender, instance=None, **kwargs):
    if not instance.is_approved():
        return
    instance.create_relation_permission()
    instance.create_relation_approved_comment()


@receiver(post_save, sender=Ticket)
def on_ticket_closed(sender, instance=None, **kwargs):
    if not instance.is_closed():
        return
    instance.create_relation_action_comment()


@receiver(m2m_changed, sender=Ticket.assignees.through)
def on_ticket_assignees_set(sender, instance=None, action=None,
                            reverse=False, model=None,
                            pk_set=None, **kwargs):
    if action == 'post_add':
        logger.debug('New ticket create, send mail: {}'.format(instance.id))
        assignees = model.objects.filter(pk__in=pk_set)
        send_new_ticket_mail_to_assignees(instance, assignees)
    if action.startswith('post') and not reverse:
        instance.assignees_display = ', '.join([
            str(u) for u in instance.assignees.all()
        ])
        instance.save()


@receiver(post_save, sender=Ticket)
def on_ticket_status_change(sender, instance=None, created=False, **kwargs):
    if created or instance.status == "open":
        return
    logger.debug('Ticket changed, send mail: {}'.format(instance.id))
    send_ticket_action_mail_to_user(instance)


@receiver(pre_save, sender=Comment)
def on_comment_create(sender, instance=None, **kwargs):
    instance.user_display = str(instance.user)
