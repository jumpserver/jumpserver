# -*- coding: utf-8 -*-
#
import json
import os
import shutil
from django.db import connections
from django.conf import LazySettings, settings
from django.db.models.signals import post_save
from django.db.utils import ProgrammingError, OperationalError
from django.dispatch import receiver
from django.db.models.signals import post_migrate
from django.utils.functional import LazyObject
from django.apps import apps
from django.core.signals import request_started

from jumpserver.const import BASE_DIR
from common.decorators import on_transaction_commit
from common.signals import django_ready
from common.utils import get_logger, ssh_key_gen
from common.utils.connection import RedisPubSub
from .const import NAS_MOUNT_PATH
from .models import Setting
from .signals import setting_changed

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


def update_site_url():
    site_url = Setting.objects.filter(name='SITE_URL').first()
    host_ip = os.environ.get('HOST_IP')
    if not host_ip:
        return
    if not site_url:
        site_url = Setting.objects.create(name='SITE_URL')

    if site_url.cleaned_value == f'http://127.0.0.1' or not site_url.cleaned_value:
        site_url.cleaned_value = f'https://{host_ip}'
        site_url.save()


@receiver(post_migrate)
def after_migrate_some_config(sender, app_config, **kwargs):
    last_app = list(apps.get_app_configs())[-1]
    if app_config.name == last_app.name:
        update_site_url()


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


@receiver(post_migrate, dispatch_uid='settings.signal_handlers.init_sqlite_db')
def init_sqlite_db(sender, app_config, **kwargs):
    if app_config.name != 'settings':
         return
    db_path = settings.LEAK_PASSWORD_DB_PATH
    if not os.path.isfile(db_path):
        # 这里处理一下历史数据，有可能用户 copy 了旧的文件到 目录下
        src = os.path.join(settings.PROJECT_DIR, 'data', 'leak_passwords.db')
        if not os.path.isfile(src):
            src = os.path.join(
                settings.APPS_DIR, 'accounts', 'automations',
                'check_account', 'leak_passwords.db'
            )
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        shutil.copy(src, db_path)
    logger.info(f'init sqlite db {db_path}')
    return db_path


@receiver(django_ready)
def register_sqlite_connection(sender, **kwargs):
    connections.databases['sqlite'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'ATOMIC_REQUESTS': False,
        'NAME': settings.LEAK_PASSWORD_DB_PATH,
        'TIME_ZONE': None,
        'CONN_HEALTH_CHECKS': False,
        'CONN_MAX_AGE': 0,
        'OPTIONS': {},
        'AUTOCOMMIT': True,
    }


@receiver(setting_changed)
def on_syslog_setting_changed(sender, name='', **kwargs):
    if name not in ('SYSLOG_HOST', 'SYSLOG_PORT', 'SYSLOG_FACILITY', 'SYSLOG_SOCKTYPE'):
        return
    try:
        from jumpserver.settings.logging import reconfigure_syslog_handler
        reconfigure_syslog_handler()
        logger.debug('Syslog handler reconfigured after %s changed', name)
    except Exception as e:
        logger.error('Failed to reconfigure syslog handler: %s', e)

@receiver(django_ready)
def on_django_ready_init_syslog_handler(sender, **kwargs):
    try:
        from jumpserver.settings.logging import reconfigure_syslog_handler
        reconfigure_syslog_handler()
    except Exception as e:
        logger.error('Failed to reconfigure syslog handler: %s', e)


@receiver(django_ready)
def on_django_ready_mount_nas(sender, **kwargs):
    """Ensure NAS is mounted when Django starts up."""
    try:
        from settings.tools.nas_mount import ensure_nas_mounted

        config = {
            'nas_enabled': getattr(settings, 'NAS_ENABLED', False),
            'nas_type': getattr(settings, 'NAS_TYPE', 'nfs'),
            'nas_host': getattr(settings, 'NAS_HOST', ''),
            'nas_port': getattr(settings, 'NAS_PORT', 0),
            'nas_share_name': getattr(settings, 'NAS_SHARE_NAME', ''),
            'nas_mount_path': NAS_MOUNT_PATH,
            'nas_username': getattr(settings, 'NAS_USERNAME', ''),
            'nas_password': getattr(settings, 'NAS_PASSWORD', ''),
        }
        ensure_nas_mounted(config)
    except Exception as e:
        logger.error('Failed to mount NAS on startup: %s', e)
