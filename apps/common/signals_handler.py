# -*- coding: utf-8 -*-
#
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.conf import LazySettings, empty
from django.db.utils import ProgrammingError, OperationalError
from django.core.cache import cache

from jumpserver.utils import current_request
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
    cache_key_prefix = '_SETTING_'

    def monkey_patch_getattr(self, name):
        key = cache_key_prefix + name
        cached = cache.get(key)
        if cached is not None:
            return cached
        if self._wrapped is empty:
            self._setup(name)
        val = getattr(self._wrapped, name)
        return val

    def monkey_patch_setattr(self, name, value):
        key = cache_key_prefix + name
        cache.set(key, value, None)
        if name == '_wrapped':
            self.__dict__.clear()
        else:
            self.__dict__.pop(name, None)
        super(LazySettings, self).__setattr__(name, value)

    def monkey_patch_delattr(self, name):
        super(LazySettings, self).__delattr__(name)
        self.__dict__.pop(name, None)
        key = cache_key_prefix + name
        cache.delete(key)

    try:
        LazySettings.__getattr__ = monkey_patch_getattr
        LazySettings.__setattr__ = monkey_patch_setattr
        LazySettings.__delattr__ = monkey_patch_delattr
        Setting.refresh_all_settings()
    except (ProgrammingError, OperationalError):
        pass


@receiver(pre_save, dispatch_uid="my_unique_identifier")
def on_create_set_created_by(sender, instance=None, **kwargs):
    if getattr(instance, '_ignore_auto_created_by', False) is True:
        return
    if hasattr(instance, 'created_by') and not instance.created_by:
        if current_request and current_request.user.is_authenticated:
            instance.created_by = current_request.user.name
