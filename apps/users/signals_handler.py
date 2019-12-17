# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django.db.models.signals import m2m_changed

from common.utils import get_logger
from .signals import post_user_create
from .models import User

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


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_change(sender, instance=None, action='', **kwargs):
    """
    资产节点发生变化时，刷新节点
    """
    if action.startswith('post'):
        logger.debug("User group member change signal recv: {}".format(instance))
        from perms.utils import AssetPermissionUtilV2
        AssetPermissionUtilV2.expire_all_user_tree_cache()
