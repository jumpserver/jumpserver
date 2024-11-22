from common.db.utils import get_logger
from .service import AZUREVaultClient
from ..base.vault import BaseVault
from ...const import VaultTypeChoices


logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):
    type = VaultTypeChoices.azure

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = AZUREVaultClient(
            vault_url=kwargs.get('VAULT_AZURE_HOST'),
            tenant_id=kwargs.get('VAULT_AZURE_TENANT_ID'),
            client_id=kwargs.get('VAULT_AZURE_CLIENT_ID'),
            client_secret=kwargs.get('VAULT_AZURE_CLIENT_SECRET')
        )

    def is_active(self):
        return self.client.is_active()

    def _get(self, entry):
        secret = self.client.get(name=entry.full_path)
        return entry.get_decrypt_secret(secret)

    def _create(self, entry):
        secret = entry.get_encrypt_secret()
        self.client.create(name=entry.full_path, secret=secret)

    def _update(self, entry):
        secret = entry.get_encrypt_secret()
        self.client.update(name=entry.full_path, secret=secret)

    def _delete(self, entry):
        self.client.delete(name=entry.full_path)

    def _save_metadata(self, entry, metadata):
        try:
            self.client.update_metadata(name=entry.full_path, metadata=metadata)
        except Exception as e:
            logger.error(f'save metadata error: {e}')
