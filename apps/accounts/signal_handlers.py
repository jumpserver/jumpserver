from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from common.utils import get_logger
from .backends import get_vault_client
from .models import Account, AccountTemplate

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if instance.version == 0:
        instance.version = 1
    else:
        instance.version = instance.history.count()


def save_to_vault(sender, instance, created, **kwargs):
    if not instance.is_sync_secret:
        return

    vault_client = get_vault_client(instance)
    if created:
        vault_client.create()
    else:
        vault_client.update()


def delete_to_vault(sender, instance, **kwargs):
    vault_client = get_vault_client(instance)
    vault_client.delete()


for model in (Account, AccountTemplate):
    post_save.connect(save_to_vault, sender=model)
    post_delete.connect(delete_to_vault, sender=model)
