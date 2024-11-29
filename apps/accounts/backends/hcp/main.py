from common.db.utils import get_logger
from .service import VaultKVClient
from ..base.vault import BaseVault

from ...const import VaultTypeChoices


logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):
    type = VaultTypeChoices.hcp

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = VaultKVClient(
            url=kwargs.get('VAULT_HCP_HOST'),
            token=kwargs.get('VAULT_HCP_TOKEN'),
            mount_point=kwargs.get('VAULT_HCP_MOUNT_POINT')
        )

    def is_active(self):
        return self.client.is_active()

    def _get(self, entry):
        # TODO: get data 是不是层数太多了
        data = self.client.get(path=entry.full_path).get('data', {})
        data = entry.get_decrypt_secret(data.get('secret'))
        return data

    def _create(self, entry):
        data = {'secret': entry.get_encrypt_secret()}
        self.client.create(path=entry.full_path, data=data)

    def _update(self, entry):
        data = {'secret': entry.get_encrypt_secret()}
        self.client.patch(path=entry.full_path, data=data)

    def _delete(self, entry):
        self.client.delete(path=entry.full_path)

    def _save_metadata(self, entry, metadata):
        try:
            self.client.update_metadata(path=entry.full_path, metadata=metadata)
        except Exception as e:
            logger.error(f'save metadata error: {e}')
