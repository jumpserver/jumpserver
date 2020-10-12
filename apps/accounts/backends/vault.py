import os
import hvac



from common.utils import get_logger
from .base import Backend

logger = get_logger(__file__)





class VaultBackend(Backend):
    # TODO: Is there need to write error log in all functions when vault server error?
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
        self.client = hvac.Client(url=self.url, token=self.token, verify=getattr(self, 'verify', None))
        if not self.client.is_authenticated():
            error_msg = 'Unable to authenticate to the Vault service'
            logger.error(error_msg)
            raise hvac.exceptions.Unauthorized(error_msg)

    @classmethod
    def get_secret_path(cls, instance):
        path = os.path.join(str(instance.org_id) or 'default_org',
                            str(instance.namespace_id) or 'default_namespace',
                            str(instance.id))
        return path

    def get_metadata(self, instance):
        path = self.get_secret_path(instance)
        meta_data = self.client.secrets.kv.v2.read_secret_metadata(
            mount_point=self.engine, path=path).get('data')
        return meta_data

    def get_secret(self, instance, version=None):
        path = self.get_secret_path(instance)
        key = self.client.secrets.kv.v2.read_secret_version(
            mount_point=self.engine, path=path, version=version).get('data').get('data').get(self.key)
        return key

    def create_secret(self, instance, data):
        """secret_data should be a k/v dict"""
        path = self.get_secret_path(instance)
        key = self.client.secrets.kv.v2.create_or_update_secret(
            mount_point=self.engine, path=path, secret=data
        )
        return key

    def update_secret(self, instance, data):
        old_secret = self.get_secret(instance)
        if old_secret != data.get(self.key):
            path = self.get_secret_path(instance)
            key = self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.engine, path=path, secret=data
            )
            return key

    def delete_secret(self, instance):
        path = self.get_secret_path(instance)
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            mount_point=self.engine, path=path
        )
