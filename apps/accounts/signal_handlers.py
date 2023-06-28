from django.db.models.signals import pre_save, m2m_changed
from django.dispatch import receiver

from common.utils import get_logger
from .models import Account, AccountProtocolConfig

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if instance.version == 0:
        instance.version = 1
    else:
        instance.version = instance.history.count()


@receiver(m2m_changed, sender=Account.configs.through)
def on_account_config_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
    print("on_account_config_changed created ................")


@receiver(pre_save, sender=AccountProtocolConfig)
def on_account_config(sender, instance, **kwargs):
    print("on_account_config created ................")
