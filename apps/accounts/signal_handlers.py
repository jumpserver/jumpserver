from django.db.models.signals import pre_save
from django.dispatch import receiver

from common.utils import get_logger
from .models import Account

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_create(sender, instance, update_fields=(), **kwargs):
    # 这是创建时
    if instance.version == 0 or instance.secret_changed():
        instance.version += 1

    # 即使在 root 组织也不怕
    instance.org_id = instance.asset.org_id
