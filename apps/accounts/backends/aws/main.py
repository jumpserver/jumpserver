from common.db.utils import get_logger
from .service import AmazonSecretsManagerClient
from ..base.vault import BaseVault
from ...const import VaultTypeChoices


logger = get_logger(__name__)

__all__ = ['Vault']


class Vault(BaseVault):
    type = VaultTypeChoices.aws

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = AmazonSecretsManagerClient(
            region_name=kwargs.get('VAULT_AWS_REGION_NAME'),
            access_key_id=kwargs.get('VAULT_AWS_ACCESS_KEY_ID'),
            secret_key=kwargs.get('VAULT_AWS_ACCESS_SECRET_KEY'),
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
