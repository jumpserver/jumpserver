from django.db.models import Model
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from ..base import BaseSecretClient
from .kv import KVEngineVault


class VaultSecretClient(BaseSecretClient):

    def __init__(self, instance: Model):
        super().__init__(instance)
        self.client = KVEngineVault(
            path=instance._meta.db_table,
            url=settings.VAULT_URL,
            token=settings.VAULT_TOKEN
        )
        if not self.client.is_active:
            raise JMSException(
                code='init_vault_fail',
                detail=_('Initialization vault fail')
            )
        self.path = self.instance.pk

    def update_or_create_secret(self):
        secret_data = self.create_secret_data()
        self.client.update_or_create(self.path, secret_data)

    def patch_secret(self, old_secret_data):
        secret_data = old_secret_data
        new_secret_data = self.create_secret_data()
        for k, v in new_secret_data.items():
            if v:
                if v != secret_data[k]:
                    secret_data[k] = v
                else:
                    del secret_data[k]
            else:
                del secret_data[k]
        if secret_data:
            self.client.patch_secret(self.path, secret_data)

    def delete_secret(self):
        self.client.complete_delete_secret(self.path)

    def get_secret(self):
        return self.client.read_secret(self.path)


client = VaultSecretClient
