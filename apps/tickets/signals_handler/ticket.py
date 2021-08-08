# -*- coding: utf-8 -*-
#
from django.dispatch import receiver

from common.utils import get_logger
from tickets.models import Ticket, TemplateApprove
from ..signals import post_change_ticket_action, post_or_update_change_template_approve

logger = get_logger(__name__)


@receiver(post_change_ticket_action, sender=Ticket)
def on_post_change_ticket_action(sender, ticket, action, **kwargs):
    ticket.handler.dispatch(action)


@receiver(post_or_update_change_template_approve, sender=TemplateApprove)
def post_or_update_change_template_approve(sender, qs, **kwargs):
    updates = []
    for instance in qs:
        instance.assignees_display = [str(assignee) for assignee in instance.assignees.all()]
        updates.append(instance)
    sender.objects.bulk_update(updates, ['assignees_display', ])
