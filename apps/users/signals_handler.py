# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django_auth_ldap.backend import populate_user
# from django.db.models.signals import post_save

from common.utils import get_logger
from .signals import post_user_create
# from .models import User

from django.db import IntegrityError
from django.db import transaction
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
    logger.debug("Receive user `{}` create signal".format(user.name))
    from .utils import send_user_created_mail
    logger.info("   - Sending welcome mail ...".format(user.name))
    if user.email:
        send_user_created_mail(user)


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user:
        user.source = user.SOURCE_LDAP
        try:
            with transaction.atomic():
                user.save()
        except IntegrityError:
            pass
