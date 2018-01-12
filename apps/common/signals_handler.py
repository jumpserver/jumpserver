# -*- coding: utf-8 -*-
#
import ldap
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.conf import settings
from django_auth_ldap.config import LDAPSearch

from .models import Setting
from .utils import get_logger
from .signals import django_ready, ldap_auth_enable

logger = get_logger(__file__)


@receiver(post_save, sender=Setting, dispatch_uid="my_unique_identifier")
def refresh_settings_on_changed(sender, instance=None, **kwargs):
    logger.debug("Receive setting item change")
    logger.debug("  - refresh setting: {}".format(instance.name))
    if instance:
        instance.refresh_setting()


@receiver(django_ready, dispatch_uid="my_unique_identifier")
def refresh_all_settings_on_django_ready(sender, **kwargs):
    logger.debug("Receive django ready signal")
    logger.debug("  - fresh all settings")
    Setting.refresh_all_settings()


@receiver(ldap_auth_enable, dispatch_uid="my_unique_identifier")
def ldap_auth_on_changed(sender, enabled=True, **kwargs):
    if enabled:
        logger.debug("Enable LDAP auth")
        if settings.AUTH_LDAP_BACKEND not in settings.AUTH_LDAP_BACKEND:
            settings.AUTHENTICATION_BACKENDS.insert(0, settings.AUTH_LDAP_BACKEND)

    else:
        logger.debug("Disable LDAP auth")
        if settings.AUTH_LDAP_BACKEND in settings.AUTHENTICATION_BACKENDS:
            settings.AUTHENTICATION_BACKENDS.remove(settings.AUTH_LDAP_BACKEND)

