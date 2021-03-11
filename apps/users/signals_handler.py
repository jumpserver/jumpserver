# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django_auth_ldap.backend import populate_user
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django_cas_ng.signals import cas_user_authenticated

from jms_oidc_rp.signals import openid_create_or_update_user

from common.utils import get_logger
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


@receiver(cas_user_authenticated)
def on_cas_user_authenticated(sender, user, created, **kwargs):
    if created and settings.ONLY_ALLOW_EXIST_USER_AUTH:
        user.delete()
        raise PermissionDenied(f'Not allow non-exist user auth: {user.username}')
    if created:
        user.source = user.Source.cas.value
        user.save()


@receiver(populate_user)
def on_ldap_create_user(sender, user, ldap_user, **kwargs):
    if user and user.username not in ['admin']:
        exists = User.objects.filter(username=user.username).exists()
        if not exists:
            user.source = user.Source.ldap.value
            user.save()


@receiver(openid_create_or_update_user)
def on_openid_create_or_update_user(sender, request, user, created, name, username, email, **kwargs):
    if created and settings.ONLY_ALLOW_EXIST_USER_AUTH:
        user.delete()
        raise PermissionDenied(f'Not allow non-exist user auth: {username}')

    if created:
        logger.debug(
            "Receive OpenID user created signal: {}, "
            "Set user source is: {}".format(user, User.Source.openid.value)
        )
        user.source = User.Source.openid.value
        user.save()
    elif not created and settings.AUTH_OPENID_ALWAYS_UPDATE_USER:
        logger.debug(
            "Receive OpenID user updated signal: {}, "
            "Update user info: {}"
            "".format(user, "name: {}|username: {}|email: {}".format(name, username, email))
        )
        user.name = name
        user.username = username
        user.email = email
        user.save()
