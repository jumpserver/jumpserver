# -*- coding: utf-8 -*-
#
import json

from django.conf import LazySettings
from django.db.models.signals import post_save
from django.db.utils import ProgrammingError, OperationalError
from django.dispatch import receiver
from django.utils.functional import LazyObject

from common.decorators import on_transaction_commit
from common.signals import django_ready
from common.utils import get_logger, ssh_key_gen
from common.utils.connection import RedisPubSub
from .models import Setting

logger = get_logger(__file__)


class SettingSubPub(LazyObject):
    def _setup(self):
        self._wrapped = RedisPubSub('settings')


setting_pub_sub = SettingSubPub()


@receiver(post_save, sender=Setting)
@on_transaction_commit
def refresh_settings_on_changed(sender, instance=None, **kwargs):
    if not instance:
        return
    setting_pub_sub.publish(instance.name)
    if instance.is_name('PERM_SINGLE_ASSET_TO_UNGROUP_NODE'):
        """ 过期所有用户授权树 """
        logger.debug('Expire all user perm tree')
        from perms.utils import UserPermTreeExpireUtil
        UserPermTreeExpireUtil().expire_perm_tree_for_all_user()


@receiver(django_ready)
def on_django_ready_add_db_config(sender, **kwargs):
    Setting.refresh_all_settings()


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


@receiver(django_ready)
def subscribe_settings_change(sender, **kwargs):
    logger.debug("Start subscribe setting change")

    setting_pub_sub.subscribe(lambda name: Setting.refresh_item(name))


@receiver(django_ready)
def monkey_patch_settings(sender, **kwargs):
    def monkey_patch_getattr(self, name):
        val = getattr(self._wrapped, name)
        # 只解析 defaults 中的 callable
        if callable(val) and val.__module__.endswith('jumpserver.conf'):
            val = val()
        return val

    try:
        LazySettings.__getattr__ = monkey_patch_getattr
    except (ProgrammingError, OperationalError):
        pass
