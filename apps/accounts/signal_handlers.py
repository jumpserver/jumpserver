from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save

from common.utils import get_logger
from assets.models import Asset
from .models import Account, PushAccountAutomation

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_create(sender, instance, **kwargs):
    # 升级版本号
    instance.version += 1
    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id


@receiver(post_save, sender=Asset)
def on_asset_create(sender, instance, created=False, **kwargs):
    if not created:
        return

    from .serializers import TriggerChoice
    automations = PushAccountAutomation.objects.filter(triggers__contains=TriggerChoice.on_asset_create)
    for automation in automations:
        pass
