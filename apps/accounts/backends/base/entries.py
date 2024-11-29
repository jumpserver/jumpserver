from abc import ABC

from common.db.utils import Encryptor
from common.utils import lazyproperty


class BaseEntry(ABC):
    def __init__(self, instance):
        self.instance = instance

    @property
    def path_base(self):
        path = f'orgs/{self.instance.org_id}'
        return path

    @lazyproperty
    def full_path(self):
        path_base = self.path_base
        path_spec = self.path_spec
        path = f'{path_base}/{path_spec}'
        return path

    @property
    def path_spec(self):
        raise NotImplementedError

    def get_encrypt_secret(self):
        secret = getattr(self.instance, '_secret', None)
        if secret is not None:
            secret = Encryptor(secret).encrypt()
        return secret

    @staticmethod
    def get_decrypt_secret(secret):
        if secret is not None:
            secret = Encryptor(secret).decrypt()
        return secret


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


class HistoricalAccountEntry(BaseEntry):
    @property
    def path_base(self):
        path = f'accounts/{self.instance.instance.id}'
        return path

    @property
    def path_spec(self):
        path = f'histories/{self.instance.history_id}'
        return path
