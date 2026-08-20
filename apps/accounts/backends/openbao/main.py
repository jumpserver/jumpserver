from common.db.utils import get_logger

from .service import OpenBaoAPIError, OpenBaoKVClient
from ..base.vault import BaseVault
from ...const import VaultTypeChoices
from ...exceptions import VaultSecretNotFoundException, VaultUnavailableException


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
        data = self._get_secret_data(entry) or {}
        return data.get('secret')

    def _get_for_restore(self, entry):
        data = self._get_secret_data(entry)
        if not isinstance(data, dict) or 'secret' not in data:
            raise VaultSecretNotFoundException()
        # None is valid for historical records that did not contain a secret.
        # Key existence distinguishes an empty secret from a missing entry.
        return data['secret']

    def _get_secret_data(self, entry):
        try:
            response = self.client.get(path=entry.full_path)
        except OpenBaoAPIError as e:
            # A missing secret is handled by the client as an empty result.  Other
            # errors mean OpenBao cannot serve this request and should be exposed
            # to API consumers as a retryable service error instead of a 500.
            logger.warning('Read secret from OpenBao failed: %s', e)
            raise VaultUnavailableException() from e
        return response.get('data')

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
