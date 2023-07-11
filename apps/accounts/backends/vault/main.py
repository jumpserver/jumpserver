from django.conf import settings

from ..base import BaseVault
from .entries import build_entry
from .service import VaultKVClient


__all__ = ['HCPVault']


class HCPVault(BaseVault):
    def __init__(self):
        self.client = VaultKVClient(
            url=settings.VAULT_HCP_HOST,
            token=settings.VAULT_HCP_TOKEN,
            mount_point=settings.VAULT_HCP_MOUNT_POINT,
        )

    def is_active(self, *args, **kwargs):
        return self.client.is_active()

    def _get(self, instance):
        entry = build_entry(instance)
        data = self.client.get(path=entry.path).get('data', {})
        return data

    def _create(self, instance):
        entry = build_entry(instance)
        data = entry.to_internal_data()
        self.client.create(path=entry.path, data=data)

    def _update(self, instance):
        entry = build_entry(instance)
        data = entry.to_internal_data()
        self.client.patch(path=entry.path, data=data)

    def _delete(self, instance):
        entry = build_entry(instance)
        self.client.delete(path=entry.path)

    def _get_histories(self, instance):
        histories = []
        entry = build_entry(instance)
        paths = entry.get_histories_paths()
        for path in paths:
            history = self.client.get(path=path).get('data', {})
            histories.append(history)
        return histories

    def _save_metadata(self, instance, metadata):
        entry = build_entry(instance)
        self.client.update_metadata(path=entry.path, metadata=metadata)
