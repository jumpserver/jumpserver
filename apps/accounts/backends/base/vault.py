import importlib
import inspect

from abc import ABC, abstractmethod

from django.forms.models import model_to_dict

from .entries import BaseEntry
from ...const import VaultTypeChoices


class BaseVault(ABC):
    def __init__(self, *args, **kwargs):
        self.enabled = kwargs.get('VAULT_ENABLED')
        self._entry_classes = {}
        self._load_entries()

    def _load_entries_import_module(self, module_name):
        module = importlib.import_module(module_name)
        for name, obj in inspect.getmembers(module, inspect.isclass):
            self._entry_classes.setdefault(name, obj)

    def _load_entries(self):
        if self.type == VaultTypeChoices.local:
            return

        module_name = f'accounts.backends.{self.type}.entries'
        if importlib.util.find_spec(module_name): # noqa
            self._load_entries_import_module(module_name)
        base_module = 'accounts.backends.base.entries'
        self._load_entries_import_module(base_module)

    @property
    @abstractmethod
    def type(self):
        raise NotImplementedError

    def get(self, instance):
        """ 返回 secret 值 """
        return self._get(self.build_entry(instance))

    def create(self, instance):
        if not instance.secret_has_save_to_vault:
            entry = self.build_entry(instance)
            self._create(entry)
            self._clean_db_secret(instance)
            self.save_metadata(entry)

    def update(self, instance):
        entry = self.build_entry(instance)
        if not instance.secret_has_save_to_vault:
            self._update(entry)
            self._clean_db_secret(instance)
            self.save_metadata(entry)

        if instance.is_sync_metadata:
            self.save_metadata(entry)

    def delete(self, instance):
        entry = self.build_entry(instance)
        self._delete(entry)

    def save_metadata(self, entry):
        metadata = model_to_dict(entry.instance, fields=[
            'name', 'username', 'secret_type',
            'connectivity', 'su_from', 'privileged'
        ])
        metadata = {k: str(v)[:500] for k, v in metadata.items() if v}
        return self._save_metadata(entry, metadata)

    def build_entry(self, instance):
        if self.type == VaultTypeChoices.local:
            return BaseEntry(instance)

        entry_class_name = f'{instance.__class__.__name__}Entry'
        entry_class = self._entry_classes.get(entry_class_name)
        if not entry_class:
            raise Exception(f'Entry class {entry_class_name} is not found')
        return entry_class(instance)

    def _clean_db_secret(self, instance):
        instance.is_sync_metadata = False
        instance.mark_secret_save_to_vault()

    # -------- abstractmethod -------- #

    @abstractmethod
    def _get(self, instance):
        raise NotImplementedError

    @abstractmethod
    def _create(self, entry):
        raise NotImplementedError

    @abstractmethod
    def _update(self, entry):
        raise NotImplementedError

    @abstractmethod
    def _delete(self, entry):
        raise NotImplementedError

    @abstractmethod
    def _save_metadata(self, instance, metadata):
        raise NotImplementedError

    @abstractmethod
    def is_active(self, *args, **kwargs) -> (bool, str):
        raise NotImplementedError
