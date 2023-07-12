import sys
from abc import ABC, abstractmethod
from common.utils import lazyproperty
from common.db.utils import Encryptor

current_module = sys.modules[__name__]

__all__ = ['build_entry']


class BaseEntry(ABC):

    def __init__(self, instance):
        self.instance = instance

    @lazyproperty
    def full_path(self):
        path_base = self.path_base
        path_spec = self.path_spec()
        path = f'{path_base}/{path_spec}'
        return path

    @property
    def path_base(self):
        path = f'orgs/{self.instance.org_id}'
        return path

    @abstractmethod
    def path_spec(self):
        raise NotImplementedError

    def to_internal_data(self):
        if self.instance.secret_need_save_to_vault():
            secret = getattr(self.instance, '_secret', '')
            secret = Encryptor(secret).encrypt()
            data = {'secret': secret}
        else:
            data = {}
        return data

    @staticmethod
    def to_external_data(data):
        secret = data.pop('secret', None)
        if secret is not None:
            secret = Encryptor(secret).decrypt()
            data.update({'secret': secret})
        return data


class AccountEntry(BaseEntry):

    @property
    def path_spec(self):
        path = f'assets/{self.instance.asset_id}/accounts/{self.instance.id}'
        return path


class AccountTemplateEntry(BaseEntry):

    @property
    def path_spec(self):
        path = f'account-templates/{self.instance.id}'
        return path


class AccountHistoricalRecordsEntry(BaseEntry):

    @property
    def path_spec(self):
        account_entry = AccountEntry(self.instance.account)
        path_histories = f'{account_entry.full_path}/histories'
        path_history = f'{path_histories}/{self.instance.id}'
        return path_history


def build_entry(instance) -> BaseEntry:
    class_name = instance.__class__.__name__
    entry_class_name = f'{class_name}Entry'
    entry_class = getattr(current_module, entry_class_name, None)
    if not entry_class:
        raise Exception(f'Entry class {entry_class_name} is not found')
    return entry_class(instance)
