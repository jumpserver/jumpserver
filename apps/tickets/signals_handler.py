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
    instance.set_display_fields()

    if instance.has_processed:
        instance.set_status_closed()


@receiver(post_save, sender=Ticket)
def on_ticket_post_save(sender, instance=None, created=False, **kwargs):

    if created and instance.action_open:
        instance.create_action_comment()
        instance.create_applied_comment()

    if not created and instance.has_processed:
        instance.create_action_comment()
        instance.create_permission()
        instance.create_approved_comment()

        logger.debug('Ticket () has processed, send mail to applicant: {}'
                     ''.format(instance.title, instance.applicant_display))
        send_ticket_processed_mail_to_applicant(instance)


@receiver(m2m_changed, sender=Ticket.assignees.through)
def on_ticket_assignees_changed(sender, instance=None, action=None, reverse=False, model=None, pk_set=None, **kwargs):
    if reverse:
        return
    if action != 'post_add':
        return
    ticket = instance
    logger.debug('Receives ticket and assignees changed signal, ticket: {}'.format(ticket.title))
    ticket.set_assignees_display()
    ticket.save()
    assignees = model.objects.filter(pk__in=pk_set)
    assignees_display = [str(assignee) for assignee in assignees]
    logger.debug('Send applied email to assignees: {}'.format(assignees_display))
    send_ticket_applied_mail_to_assignees(ticket, assignees)


@receiver(pre_save, sender=Comment)
def on_comment_create(sender, instance=None, created=False, **kwargs):
    instance.set_display_fields()
