# -*- coding: utf-8 -*-
#

from django.dispatch import Signal, receiver

from common.utils import get_logger

logger = get_logger(__file__)
on_user_created = Signal(providing_args=['user'])


@receiver(on_user_created)
def send_user_add_mail_to_user(sender, user=None, **kwargs):
    from .utils import send_user_created_mail
    logger.debug("Receive asset create signal, update asset hardware info")
    send_user_created_mail(user)

