# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import m2m_changed

from common.utils import get_logger
from tickets.models import Ticket
from tickets.utils import send_ticket_applied_mail_to_assignees
from ..signals import post_change_ticket_action
from ..handler import get_ticket_handler


logger = get_logger(__name__)


@receiver(post_change_ticket_action, sender=Ticket)
def on_post_change_ticket_action(sender, ticket, action, **kwargs):
    handler = get_ticket_handler(ticket)
    handler.dispatch(action)


@receiver(m2m_changed, sender=Ticket.assignees.through)
def on_ticket_assignees_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    if reverse:
        return
    if action != 'post_add':
        return
    logger.debug('Receives ticket and assignees changed signal, ticket: {}'.format(instance.title))
    instance.assignees_display = [str(assignee) for assignee in instance.assignees.all()]
    instance.save()
    assignees = model.objects.filter(pk__in=pk_set)
    assignees_display = [str(assignee) for assignee in assignees]
    logger.debug('Send applied email to assignees: {}'.format(assignees_display))
    send_ticket_applied_mail_to_assignees(instance, assignees)

