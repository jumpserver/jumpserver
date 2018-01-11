# -*- coding: utf-8 -*-
#

from django.dispatch import receiver
from django.db.models.signals import post_save

from .models import Setting
from .utils import get_logger
from .signals import django_ready


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
