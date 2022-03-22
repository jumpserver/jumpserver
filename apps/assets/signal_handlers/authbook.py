from django.dispatch import receiver
from django.apps import apps
from simple_history.signals import pre_create_historical_record
from django.db.models.signals import post_save, pre_save, pre_delete

from common.utils import get_logger
from ..models import AuthBook, SystemUser

AuthBookHistory = apps.get_model('assets', 'HistoricalAuthBook')
logger = get_logger(__name__)


@receiver(pre_create_historical_record, sender=AuthBookHistory)
def pre_create_historical_record_callback(sender, history_instance=None, **kwargs):
    attrs_to_copy = ['username', 'password', 'private_key']

    for attr in attrs_to_copy:
        if getattr(history_instance, attr):
            continue
        try:
            system_user = history_instance.systemuser
        except SystemUser.DoesNotExist:
            continue
        if not system_user:
            continue
        system_user_attr_value = getattr(history_instance.systemuser, attr)
        if system_user_attr_value:
            setattr(history_instance, attr, system_user_attr_value)


@receiver(pre_delete, sender=AuthBook)
def on_authbook_post_delete(sender, instance, **kwargs):
    instance.remove_asset_admin_user_if_need()


@receiver(post_save, sender=AuthBook)
def on_authbook_post_create(sender, instance, created, **kwargs):
    instance.sync_to_system_user_account()
    if created:
        pass
        # # 不再自动更新资产管理用户，只允许用户手动指定。
        # 只在创建时进行更新资产的管理用户
        # instance.update_asset_admin_user_if_need()


@receiver(pre_save, sender=AuthBook)
def on_authbook_pre_create(sender, instance, **kwargs):
    # 升级版本号
    instance.version += 1
    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id
