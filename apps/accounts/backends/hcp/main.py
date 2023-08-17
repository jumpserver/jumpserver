from common.db.utils import get_logger
from .entries import build_entry
from .service import VaultKVClient
from ..base import BaseVault

__all__ = ['Vault']

logger = get_logger(__name__)


class Vault(BaseVault):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client = VaultKVClient(
            url=kwargs.get('VAULT_HCP_HOST'),
            token=kwargs.get('VAULT_HCP_TOKEN'),
            mount_point=kwargs.get('VAULT_HCP_MOUNT_POINT')
        )

    def is_active(self):
        return self.client.is_active()

    def _get(self, instance):
        entry = build_entry(instance)
        # TODO: get data 是不是层数太多了
        data = self.client.get(path=entry.full_path).get('data', {})
        data = entry.to_external_data(data)
        return data

    def _create(self, instance):
        entry = build_entry(instance)
        data = entry.to_internal_data()
        self.client.create(path=entry.full_path, data=data)

    def _update(self, instance):
        entry = build_entry(instance)
        data = entry.to_internal_data()
        self.client.patch(path=entry.full_path, data=data)

    def _delete(self, instance):
        entry = build_entry(instance)
        self.client.delete(path=entry.full_path)

    def _clean_db_secret(self, instance):
        instance.is_sync_metadata = False
        instance.mark_secret_save_to_vault()

    def _save_metadata(self, instance, metadata):
        try:
            entry = build_entry(instance)
            self.client.update_metadata(path=entry.full_path, metadata=metadata)
        except Exception as e:
            logger.error(f'save metadata error: {e}')
