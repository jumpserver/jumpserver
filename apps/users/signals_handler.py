# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django.db.models.signals import m2m_changed
from django_auth_ldap.backend import populate_user
from django.conf import settings
from django_cas_ng.signals import cas_user_authenticated

from jms_oidc_rp.signals import oidc_user_created, oidc_user_updated
from jms_oidc_rp.backends import get_userinfo_from_claims

from common.utils import get_logger
from .utils import construct_user_email
from .signals import post_user_create
from .models import User


logger = get_logger(__file__)


@receiver(post_user_create)
def on_user_create(sender, user=None, **kwargs):
    logger.debug("Receive user `{}` create signal".format(user.name))
    from .utils import send_user_created_mail
    logger.info("   - Sending welcome mail ...".format(user.name))
    if user.can_send_created_mail():
        send_user_created_mail(user)


@receiver(m2m_changed, sender=User.groups.through)
def on_user_groups_change(sender, instance=None, action='', **kwargs):
    """
    资产节点发生变化时，刷新节点
    """
    if action.startswith('post'):
        logger.debug("User group member change signal recv: {}".format(instance))
        from perms.utils import AssetPermissionUtil
        AssetPermissionUtil.expire_all_user_tree_cache()


@receiver(cas_user_authenticated)
def on_cas_user_authenticated(sender, user, created, **kwargs):
    if created:
        user.source = user.SOURCE_CAS
        user.save()


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.username not in ['admin']:
        exists = User.objects.filter(username=user.username).exists()
        if not exists:
            user.source = user.SOURCE_LDAP
            user.save()


@receiver(oidc_user_created)
def on_oidc_user_created(sender, request, oidc_user, **kwargs):
    oidc_user.user.source = User.SOURCE_OPENID
    oidc_user.user.save()


@receiver(oidc_user_updated)
def on_oidc_user_updated(sender, request, oidc_user, **kwargs):
    if not settings.AUTH_OPENID_ALWAYS_UPDATE_USER_INFORMATION:
        return
    name, username, email = get_userinfo_from_claims(oidc_user.userinfo)
    email = construct_user_email(username, email)
    oidc_user.user.name = name
    oidc_user.user.username = username
    oidc_user.user.email = email
    oidc_user.user.save()
