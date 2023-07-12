from abc import ABC, abstractmethod
from django.forms.models import model_to_dict

__all__ = ['BaseVault']


class BaseVault(ABC):
    def create(self, instance):
        self._create(instance)
        self._clean_db_secret(instance)
        self.save_metadata(instance)

    def update(self, instance):
        self._update(instance)
        self._clean_db_secret(instance)
        self.save_metadata(instance)

    def delete(self, instance):
        self._delete(instance)

    def get(self, instance):
        return self._get(instance)

    def save_metadata(self, instance):
        metadata = model_to_dict(instance, exclude=['id'])
        metadata = {field: str(value) for field, value in metadata.items()}
        return self._save_metadata(instance, metadata)

    @staticmethod
    def _clean_db_secret(instance):
        instance.mark_secret_save_to_vault()

    # -------- abstractmethod -------- #

    @abstractmethod
    def is_active(self, *args, **kwargs):
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
    def _get(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _save_metadata(self, instance, metadata):
        raise NotImplementedError
