# -*- coding: utf-8 -*-
#
import json

from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save

from jumpserver.utils import current_request
from common.utils import get_logger, ssh_key_gen
from common.signals import django_ready
from .models import Setting

logger = get_logger(__file__)


@receiver(post_save, sender=Setting, dispatch_uid="my_unique_identifier")
def refresh_settings_on_changed(sender, instance=None, **kwargs):
    if instance:
        instance.refresh_setting()


@receiver(django_ready)
def on_django_ready_add_db_config(sender, **kwargs):
    from django.conf import settings
    settings.DYNAMIC.db_setting = Setting


@receiver(django_ready)
def auto_generate_terminal_host_key(sender, **kwargs):
    try:
        if Setting.objects.filter(name='TERMINAL_HOST_KEY').exists():
            return
        private_key, public_key = ssh_key_gen()
        value = json.dumps(private_key)
        Setting.objects.create(name='TERMINAL_HOST_KEY', value=value)
    except:
        pass


@receiver(pre_save, dispatch_uid="my_unique_identifier")
def on_create_set_created_by(sender, instance=None, **kwargs):
    if getattr(instance, '_ignore_auto_created_by', False) is True:
        return
    if hasattr(instance, 'created_by') and not instance.created_by:
        if current_request and current_request.user.is_authenticated:
            instance.created_by = current_request.user.name
