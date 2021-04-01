import hvac
from hvac import utils
from ..models import Account
from .base import BaseBackends


__all__ = ['VaultBackend']


class VaultBackend(BaseBackends):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        url = kwargs.get('url')
        token = kwargs.get('token')
        secrets_engine_path = kwargs.get('secrets_engine_path', '')

        self.client = hvac.Client(url=url, token=token)
        self.secrets_max_versions = 20
        self.secrets_engine_type = 'kv-v2'
        self.secrets_engine_path = '{}/'.format(secrets_engine_path.rstrip('/'))
        self.enable_secrets_engine()

    def enable_secrets_engine(self):
        # check
        secrets_engines = self.client.sys.list_mounted_secrets_engines()
        secrets_engines_paths = secrets_engines.keys()
        if self.secrets_engine_path in secrets_engines_paths:
            return
        # enable
        self.client.sys.enable_secrets_engine(
            backend_type=self.secrets_engine_type,
            path=self.secrets_engine_path
        )
        # config
        self.client.secrets.kv.v2.configure(
            max_versions=self.secrets_max_versions,
            mount_point=self.secrets_engine_path
        )

    def update_secret(self, account, secret_data: dict):
        return self.create_secret(account, secret_data)

    def update_or_create(self, account, secret_data: dict):
        return self.create_secret(account, secret_data)

    def create_secret(self, account, secret_data: dict):
        path = self.construct_path_of_account(account)
        response = self.client.secrets.kv.v2.create_or_update_secret(
            path=path, secret=secret_data, mount_point=self.secrets_engine_path
        )
        return response

    def delete_secret(self, account):
        path = self.construct_path_of_account(account)
        versions = self.get_secret_versions(account)
        self.client.secrets.kv.v2.delete_secret_versions(
            path=path, versions=versions, mount_point=self.secrets_engine_path,
        )

    def undelete_secret(self, account):
        """ The reserved interface """
        path = self.construct_path_of_account(account)
        versions = self.get_secret_versions(account)
        self.client.secrets.kv.v2.undelete_secret_versions(
            path=path, versions=versions, mount_point=self.secrets_engine_path,
        )

    def read_secret(self, account, version=None):
        path = self.construct_path_of_account(account)
        response = self.client.secrets.kv.v2.read_secret_version(
            path=path, version=version, mount_point=self.secrets_engine_path,
        )
        secret_data = response.get('data', {}).get('data')
        return secret_data

    def get_secret_versions(self, account):
        metadata = self.read_secret_metadata(account)
        oldest_version = metadata['data']['oldest_version']
        current_version = metadata['data']['current_version']
        versions = list(range(oldest_version, current_version+1))
        return versions

    def read_secret_metadata(self, account):
        path = self.construct_path_of_account(account)
        metadata = self.client.secrets.kv.v2.read_secret_metadata(
            path=path, mount_point=self.secrets_engine_path
        )
        return metadata

    @staticmethod
    def construct_path_of_account(account: Account):
        path = '/'.join([account.org_id, str(account.safe_id), str(account.id)])
        return path
