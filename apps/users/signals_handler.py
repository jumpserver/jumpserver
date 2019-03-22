# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
# from django.db.models.signals import post_save
from django_auth_ldap.backend import populate_user
from django.contrib.auth.signals import user_logged_in

from common.utils import get_logger
from .signals import post_user_create
# from .models import User
from .utils import check_ldap_user_group_relation
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


#@receiver(populate_user)
#def on_ldap_create_user(sender, user, ldap_user, **kwargs):
#    #logger.debug(">>>>>>>>>> LDAPUSER:")
#    #logger.debug(str(ldap_user.group_names))
#    #logger.debug(">>>>>>>>>>>>>>>USER:")
#    #logger.debug(str(user.groups))
#    if user and user.name != 'admin':
#        #user.source = user.SOURCE_LDAP
#        if user.groups.count() == 0:
#            logger.debug("users group count == 0")
#            user.save()


def sync_ldap_user_groups(sender, user, request, **kwargs):
    if user.source == "ldap":
        check_ldap_user_group_relation(user)
    else:
        logger.error("user is not ldap user" )

user_logged_in.connect(sync_ldap_user_groups)
