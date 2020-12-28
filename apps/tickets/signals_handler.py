# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import m2m_changed, post_save, pre_save

from common.utils import get_logger
from .models import Ticket, Comment
from .utils import (
    send_ticket_applied_mail_to_assignees,
    send_ticket_processed_mail_to_applicant
)
from . import const


logger = get_logger(__name__)


@receiver(pre_save, sender=Ticket)
def on_ticket_pre_save(sender, instance=None, **kwargs):
    if instance.is_applied:
        instance.applicant_display = str(instance.applicant)
    if instance.is_processed:
        instance.processor_display = str(instance.processor)
        instance.status = const.TicketStatusChoices.closed.value


@receiver(post_save, sender=Ticket)
def on_ticket_processed(sender, instance=None, created=False, **kwargs):
    if not instance.is_processed:
        return
    logger.debug('Ticket is processed, send mail: {}'.format(instance.id))
    instance.create_action_comment()
    if instance.is_approved:
        instance.create_permission()
        instance.create_approved_comment()
    send_ticket_processed_mail_to_applicant(instance)


@receiver(m2m_changed, sender=Ticket.assignees.through)
def on_ticket_assignees_changed(sender, instance=None, action=None, reverse=False, model=None, pk_set=None, **kwargs):
    if action == 'post_add':
        logger.debug('New ticket create, send mail: {}'.format(instance.title))
        assignees = model.objects.filter(pk__in=pk_set)
        send_ticket_applied_mail_to_assignees(instance, assignees)
    if action.startswith('post') and not reverse:
        assignees_display = [str(assignee) for assignee in instance.assignees.all()]
        instance.assignees_display = ', '.join(assignees_display)
        instance.save()


@receiver(pre_save, sender=Comment)
def on_comment_create(sender, instance=None, created=False, **kwargs):
    instance.user_display = str(instance.user)
