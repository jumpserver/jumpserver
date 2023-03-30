from django.db.models.signals import pre_save
from django.dispatch import receiver

from common.utils import get_logger
from .models import Account

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if instance.version == 0:
        instance.version = 1
    else:
        instance.version = instance.history.count()
