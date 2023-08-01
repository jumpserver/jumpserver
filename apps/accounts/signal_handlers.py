from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver

from accounts.backends import vault_client
from common.utils import get_logger
from .models import Account, AccountTemplate

logger = get_logger(__name__)


@receiver(pre_save, sender=Account)
def on_account_pre_save(sender, instance, **kwargs):
    if instance.version == 0:
        instance.version = 1
    else:
        instance.version = instance.history.count()


class VaultSignalHandler(object):
    """ 处理 Vault 相关的信号 """

    @staticmethod
    def save_to_vault(sender, instance, created, **kwargs):
        if created:
            vault_client.create(instance)
        else:
            vault_client.update(instance)

    @staticmethod
    def delete_to_vault(sender, instance, **kwargs):
        vault_client.delete(instance)


for model in (Account, AccountTemplate, Account.history.model):
    post_save.connect(VaultSignalHandler.save_to_vault, sender=model)
    post_delete.connect(VaultSignalHandler.delete_to_vault, sender=model)
