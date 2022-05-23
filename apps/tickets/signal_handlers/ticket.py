# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import post_save, m2m_changed

from common.decorator import on_transaction_commit
from common.utils import get_logger
from tickets.models import Ticket
from ..signals import post_change_ticket_action

logger = get_logger(__name__)


@receiver(post_change_ticket_action, sender=Ticket)
def on_post_change_ticket_action(sender, ticket, action, **kwargs):
    ticket.handler.dispatch(action)


@receiver(post_save, sender=Ticket)
def on_pre_save_ensure_serial_num(sender, instance: Ticket, **kwargs):
    instance.update_serial_num_if_need()


@receiver(post_save, sender=Ticket)
@on_transaction_commit
def after_save_set_rel_snapshot(sender, instance, created=False, **kwargs):
    print("Ticket save siagnal rewith ")
    if created:
        instance.set_rel_snapshot()


@receiver(m2m_changed, sender=Ticket)
@on_transaction_commit
def on_m2m_change(sender, action, instance, reverse, **kwargs):
    if action.startswith('post'):
        instance.set_rel_snapshot()
