# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
# from django.db.models.signals import post_save

from common.utils import get_logger
from .signals import post_user_create
# from .models import User

logger = get_logger(__file__)


# @receiver(post_save, sender=User)
# def on_user_created(sender, instance=None, created=False, **kwargs):
#     if created:
#         logger.debug("Receive user `{}` create signal".format(instance.name))
#         from .utils import send_user_created_mail
#         logger.info("   - Sending welcome mail ...".format(instance.name))
#         if instance.email:
#             send_user_created_mail(instance)


@receiver(post_user_create)
def on_user_create(sender, user=None, **kwargs):
    from .utils import send_user_created_mail
    if isinstance(user, list):
        for obj in user:
            logger.debug("Receive user `{}` create signal".format(obj.name))
            logger.info("   - Sending welcome mail ...".format(obj.name))
            if obj.email:
                send_user_created_mail(obj)
    else:
        logger.debug("Receive user `{}` create signal".format(user.name))
        logger.info("   - Sending welcome mail ...".format(user.name))
        if user.email:
            send_user_created_mail(user)

