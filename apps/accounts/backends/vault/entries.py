import sys
from abc import ABC, abstractmethod
from common.utils import lazyproperty

current_module = sys.modules[__name__]

__all__ = ['build_entry']


class BaseEntry(ABC):

    def __init__(self, instance):
        self.instance = instance

    @lazyproperty
    def path(self):
        base_path = self.get_base_path()
        spec_pth = self.get_spec_path()
        path = f'{base_path}/{spec_pth}'
        return path

    def get_base_path(self):
        path = f'orgs/{self.instance.org_id}'
        return path

    @abstractmethod
    def get_spec_path(self):
        raise NotImplementedError

    def to_internal_data(self):
        # TODO: _secret 到底是否加密是个问题, Model Field 层面还是要默认加密
        secret = getattr(self.instance, '_secret', '')
        return {'secret': secret}

    def get_histories_paths(self):
        return []


class AccountEntry(BaseEntry):

    def get_spec_path(self):
        path = f'assets/{self.instance.asset_id}/accounts/{self.instance.id}'
        return path

    def get_histories_paths(self):
        ids = self.instance.history.all().values_list('id', flat=True)
        paths = [f'{self.path}/histories/{i}' for i in ids]
        return paths


class AccountTemplateEntry(BaseEntry):

    def get_spec_path(self):
        path = f'account-templates/{self.instance.id}'
        return path


class AccountHistoricalRecordsEntry(BaseEntry):

    def get_spec_path(self):
        account_entry = AccountEntry(self.instance.account)
        path_account = account_entry.get_spec_path()
        path_history = f'histories/{self.instance.id}'
        path = f'{path_account}/{path_history}'
        return path

    def to_internal_data(self):
        from accounts.serializers import AccountHistorySerializer
        serializer = AccountHistorySerializer(instance=self.instance)
        data = super().to_internal_data()
        data.update(serializer.data)
        return data


def build_entry(instance) -> BaseEntry:
    class_name = instance.__class__.__name__
    entry_class_name = f'{class_name}Entry'
    entry_class = getattr(current_module, entry_class_name, None)
    if not entry_class:
        raise Exception(f'Entry class {entry_class_name} is not found')
    return entry_class(instance)
