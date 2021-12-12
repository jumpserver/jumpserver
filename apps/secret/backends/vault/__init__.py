from django.db.models import Model
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from common.utils import get_logger
from ..base import BaseSecretClient
from .kv import KVEngineVault

logger = get_logger(__name__)


class VaultSecretClient(BaseSecretClient):

    def __init__(self, instance: Model):
        super().__init__(instance)
        app_label = instance._meta.app_label
        object_name = instance._meta.object_name
        self.client = KVEngineVault(
            settings.VAULT_PATH,
            url=settings.VAULT_URL,
            token=settings.VAULT_TOKEN
        )
        if not self.client.is_active:
            raise JMSException(
                code='init_vault_fail',
                detail=_('Initialization vault fail')
            )
        self.path = f'{app_label}/{object_name}/{self.instance.pk}'

    def create_secret(self, secret_data=None):
        logger.debug(f'Vault is creating {self.instance}')
        if not secret_data:
            secret_data = self.create_secret_data()
        self.client.update_or_create(self.path, secret_data)

    def patch_secret(self, old_secret_data):
        logger.debug(f'Vault is updating {self.instance}')
        secret_data = self.get_change_secret_data(old_secret_data)
        if secret_data:
            self.client.patch_secret(self.path, secret_data)

    def delete_secret(self):
        logger.debug(f'Vault is deleting {self.instance}')
        self.client.complete_delete_secret(self.path)

    def get_secret(self):
        return self.client.read_secret(self.path)


client = VaultSecretClient
