from common.db.utils import get_logger
from .entries import build_entry
from .service import AZUREVaultClient
from ..base import BaseVault

__all__ = ['Vault']

logger = get_logger(__name__)


class Vault(BaseVault):
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

    def _get(self, instance):
        entry = build_entry(instance)
        secret = self.client.get(name=entry.full_path)
        secret = entry.to_external_data(secret)
        return secret

    def _create(self, instance):
        entry = build_entry(instance)
        secret = entry.to_internal_data()
        self.client.create(name=entry.full_path, secret=secret)

    def _update(self, instance):
        entry = build_entry(instance)
        secret = entry.to_internal_data()
        self.client.update(name=entry.full_path, secret=secret)

    def _delete(self, instance):
        entry = build_entry(instance)
        self.client.delete(name=entry.full_path)

    def _clean_db_secret(self, instance):
        instance.is_sync_metadata = False
        instance.mark_secret_save_to_vault()

    def _save_metadata(self, instance, metadata):
        try:
            entry = build_entry(instance)
            self.client.update_metadata(name=entry.full_path, metadata=metadata)
        except Exception as e:
            logger.error(f'save metadata error: {e}')
