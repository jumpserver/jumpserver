# -*- coding: utf-8 -*-
#
import json

from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.conf import LazySettings, empty, global_settings
from django.db.utils import ProgrammingError, OperationalError
from django.core.cache import cache

from jumpserver.utils import current_request
from common.utils import get_logger, ssh_key_gen
from common.signals import django_ready
from .models import Setting

logger = get_logger(__file__)


@receiver(post_save, sender=Setting, dispatch_uid="my_unique_identifier")
def refresh_settings_on_changed(sender, instance=None, **kwargs):
    if instance:
        instance.refresh_setting()


@receiver(django_ready, dispatch_uid="my_unique_identifier")
def monkey_patch_settings(sender, **kwargs):
    cache_key_prefix = '_SETTING_'
    custom_need_cache_settings = [
        'AUTHENTICATION_BACKENDS'
    ]
    custom_no_cache_settings = [
        'BASE_DIR', 'VERSION', 'AUTH_OPENID'
    ]
    django_settings = dir(global_settings)
    uncached_settings = [i for i in django_settings if i.isupper()]
    uncached_settings = [i for i in uncached_settings if not i.startswith('EMAIL')]
    uncached_settings = [i for i in uncached_settings if not i.startswith('SESSION_REDIS')]
    uncached_settings = [i for i in uncached_settings if i not in custom_need_cache_settings]
    uncached_settings.extend(custom_no_cache_settings)

    def monkey_patch_getattr(self, name):
        if name not in uncached_settings:
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
        cache.delete_pattern(cache_key_prefix+'*')
        LazySettings.__getattr__ = monkey_patch_getattr
        LazySettings.__setattr__ = monkey_patch_setattr
        LazySettings.__delattr__ = monkey_patch_delattr
        Setting.refresh_all_settings()
    except (ProgrammingError, OperationalError):
        pass


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
