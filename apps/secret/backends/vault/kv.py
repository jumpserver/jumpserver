from hvac import exceptions
from common.utils import get_logger
from .base import BaseVault

__all__ = ['KVEngineVault', ]

logger = get_logger(__name__)


class KVEngineVault(BaseVault):

    def __init__(self, path, url=None, token=None):
        super().__init__(url, token)
        secrets_max_versions = 5
        assert isinstance(secrets_max_versions, int) and 3 <= secrets_max_versions, (
            'secrets_max_versions must to be an integer that is greater than or equal to 3'
        )

        self.secrets_max_versions = secrets_max_versions
        self.secrets_engine_type = 'kv-v2'
        self.secrets_engine_path = 'jms({})/'.format(path)
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
        import time
        time.sleep(1)
        # config
        self.client.secrets.kv.v2.configure(
            max_versions=self.secrets_max_versions,
            mount_point=self.secrets_engine_path
        )

    def read_secret_metadata(self, path):
        try:
            metadata = self.client.secrets.kv.v2.read_secret_metadata(
                path=path, mount_point=self.secrets_engine_path
            )
        except exceptions.InvalidPath as e:
            logger.error('Read secret metadata error: {}'.format(str(e)))
            metadata = {}
        return metadata

    def get_secret_versions(self, path):
        metadata = self.read_secret_metadata(path)
        if not metadata:
            return []
        oldest_version = metadata['data']['oldest_version']
        current_version = metadata['data']['current_version']
        versions = list(range(oldest_version, current_version + 1))
        return versions

    def read_secret(self, path, version=None):
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, version=version, mount_point=self.secrets_engine_path,
            )
            secret_data = response.get('data', {}).get('data', {})
        except exceptions.InvalidPath as e:
            logger.error('Read secret error: {}'.format(str(e)))
            secret_data = {}
        return secret_data

    def patch_secret(self, path, secret_data: dict):
        try:
            response = self.client.secrets.kv.v2.patch(
                path=path, secret=secret_data, mount_point=self.secrets_engine_path
            )
        except exceptions.InvalidPath as e:
            logger.error('Patch secret error: {}'.format(e))
            response = None
        return response

    def update_or_create(self, path, secret_data: dict):
        try:
            response = self.client.secrets.kv.v2.create_or_update_secret(
                path=path, secret=secret_data, mount_point=self.secrets_engine_path
            )
        except exceptions.InvalidPath as e:
            logger.error('Create or update secret error: {}'.format(e))
            response = None
        return response

    def delete_secret(self, path):
        versions = self.get_secret_versions(path)
        if not versions:
            return
        self.client.secrets.kv.v2.delete_secret_versions(
            path=path, versions=versions, mount_point=self.secrets_engine_path,
        )

    def undelete_secret(self, path):
        versions = self.get_secret_versions(path)
        if not versions:
            return
        self.client.secrets.kv.v2.undelete_secret_versions(
            path=path, versions=versions, mount_point=self.secrets_engine_path,
        )

    def complete_delete_secret(self, path):
        versions = self.get_secret_versions(path)
        if not versions:
            return
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path, versions=versions, mount_point=self.secrets_engine_path,
        )
