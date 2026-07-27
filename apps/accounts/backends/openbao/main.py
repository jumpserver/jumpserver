from common.db.utils import get_logger

from .service import OpenBaoKVClient
from ..base.vault import BaseVault
from ...const import VaultTypeChoices


logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):
    type = VaultTypeChoices.openbao

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = OpenBaoKVClient(
            addr=kwargs.get('VAULT_OPENBAO_ADDR'),
            token=kwargs.get('VAULT_OPENBAO_TOKEN'),
            mount_point=kwargs.get('VAULT_OPENBAO_MOUNT_POINT'),
            timeout=kwargs.get('VAULT_OPENBAO_TIMEOUT'),
        )

    def is_active(self):
        return self.client.is_active()

    def _get(self, entry):
        data = self.client.get(path=entry.full_path).get('data', {})
        return data.get('secret')

    def _create(self, entry):
        data = {'secret': self._get_plain_secret(entry)}
        self.client.create(path=entry.full_path, data=data)

    def _update(self, entry):
        data = {'secret': self._get_plain_secret(entry)}
        self.client.patch(path=entry.full_path, data=data)

    def _delete(self, entry):
        self.client.delete(path=entry.full_path)

    def _save_metadata(self, entry, metadata):
        try:
            asset = getattr(entry.instance, 'asset', None)
            address = getattr(asset, 'address', None)
            if address:
                metadata['asset_address'] = str(address)[:500]
            self.client.update_metadata(path=entry.full_path, metadata=metadata)
        except Exception as e:
            logger.error(f'save metadata error: {e}')

    @staticmethod
    def _get_plain_secret(entry):
        return getattr(entry.instance, '_secret', None)
