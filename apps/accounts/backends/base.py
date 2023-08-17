from abc import ABC, abstractmethod

from django.forms.models import model_to_dict

__all__ = ['BaseVault']


class BaseVault(ABC):

    def __init__(self, *args, **kwargs):
        self.enabled = kwargs.get('VAULT_ENABLED')

    def get(self, instance):
        """ 返回 secret 值 """
        return self._get(instance)

    def create(self, instance):
        if not instance.secret_has_save_to_vault:
            self._create(instance)
            self._clean_db_secret(instance)
            self.save_metadata(instance)

        if instance.is_sync_metadata:
            self.save_metadata(instance)

    def update(self, instance):
        if not instance.secret_has_save_to_vault:
            self._update(instance)
            self._clean_db_secret(instance)
            self.save_metadata(instance)

        if instance.is_sync_metadata:
            self.save_metadata(instance)

    def delete(self, instance):
        self._delete(instance)

    def save_metadata(self, instance):
        metadata = model_to_dict(instance, fields=[
            'name', 'username', 'secret_type',
            'connectivity', 'su_from', 'privileged'
        ])
        metadata = {k: str(v)[:500] for k, v in metadata.items() if v}
        return self._save_metadata(instance, metadata)

    # -------- abstractmethod -------- #

    @abstractmethod
    def _get(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _create(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _update(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _delete(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _clean_db_secret(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _save_metadata(self, instance, metadata):
        raise NotImplementedError

    @abstractmethod
    def is_active(self, *args, **kwargs) -> (bool, str):
        raise NotImplementedError
