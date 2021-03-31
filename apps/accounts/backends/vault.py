import hvac
from ..models import Account
from .base import BaseBackends


class VaultBackend(BaseBackends):

    def __init__(self, **kwargs):
        self.client = hvac.Client(url='', )
        self.secrets_engine_name = 'JumpServerAccounts/'
        self.enable_secretes_engine()
        super().__init__(**kwargs)

    def enable_secretes_engine(self):
        secrets_engines = self.client.sys.list_mounted_secrets_engines()
        if self.secrets_engine_name not in secrets_engines.keys():
            self.client.sys.enable_secrets_engine(backend_type='kv', path=self.secrets_engine_name)

    def create_secret(self, account: Account, secret: str):
        pass

    def update_secret(self, account: Account, secret: str):
        pass

    def delete_secret(self, account: Account):
        pass

    def get_secret(self, account: Account):
        pass
