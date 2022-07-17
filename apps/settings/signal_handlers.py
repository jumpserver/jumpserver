# -*- coding: utf-8 -*-
#
import json
import threading

from django.conf import LazySettings
from django.db.utils import ProgrammingError, OperationalError
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from django.utils.functional import LazyObject

from jumpserver.utils import current_request
from common.decorator import on_transaction_commit
from common.utils import get_logger, ssh_key_gen
from common.utils.connection import RedisPubSub
from common.signals import django_ready
from .models import Setting

logger = get_logger(__file__)


def get_settings_pub_sub():
    return RedisPubSub('settings')


class SettingSubPub(LazyObject):
    def _setup(self):
        self._wrapped = get_settings_pub_sub()


setting_pub_sub = SettingSubPub()


@receiver(post_save, sender=Setting)
@on_transaction_commit
def refresh_settings_on_changed(sender, instance=None, **kwargs):
    if not instance:
        return

    setting_pub_sub.publish(instance.name)

    # 配置变化: PERM_SINGLE_ASSET_TO_UNGROUP_NODE
    if instance.name == 'PERM_SINGLE_ASSET_TO_UNGROUP_NODE':
        # 清除所有用户授权树已构建的标记，下次访问重新生成
        logger.debug('Clean ALL User perm tree built mark')
        from perms.utils.asset import UserGrantedTreeRefreshController
        UserGrantedTreeRefreshController.clean_all_user_tree_built_mark()


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


@receiver(pre_save, dispatch_uid="my_unique_identifier")
def on_create_set_created_by(sender, instance=None, **kwargs):
    if getattr(instance, '_ignore_auto_created_by', False) is True:
        return
    if not hasattr(instance, 'created_by') or instance.created_by:
        return
    if current_request and current_request.user.is_authenticated:
        user_name = current_request.user.name
        if isinstance(user_name, str):
            user_name = user_name[:30]
        instance.created_by = user_name


@receiver(django_ready)
def subscribe_settings_change(sender, **kwargs):
    logger.debug("Start subscribe setting change")

    def keep_subscribe_settings_change():
        setting_pub_sub.subscribe(lambda name: Setting.refresh_item(name))

    t = threading.Thread(target=keep_subscribe_settings_change)
    t.daemon = True
    t.start()


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
