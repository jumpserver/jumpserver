from abc import ABC, abstractmethod
from django.forms.models import model_to_dict

__all__ = ['BaseVault']


class BaseVault(ABC):
    def get(self, instance):
        return self._get(instance)

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

    def save_metadata(self, instance):
        metadata = model_to_dict(instance)
        metadata = {field: str(value) for field, value in metadata.items()}
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
        pass

    @abstractmethod
    def _save_metadata(self, instance, metadata):
        raise NotImplementedError

    @abstractmethod
    def is_active(self, *args, **kwargs):
        raise NotImplementedError

