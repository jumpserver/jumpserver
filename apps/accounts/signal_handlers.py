from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver

from assets.models import Asset
from common.decorators import on_transaction_commit
from common.utils import get_logger
from .models import Account

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_create(sender, instance, **kwargs):
    # 升级版本号
    instance.version += 1
    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id


@receiver(post_save, sender=Asset)
@on_transaction_commit
def on_asset_create(sender, instance, created=False, **kwargs):
    if not created:
        return
    # PushAccountManager.trigger_by_asset_create(instance)
