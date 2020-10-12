import os
import hvac


from common.utils import get_logger
from .base import Backend

logger = get_logger(__file__)


class VaultBackend(Backend):
    # TODO: Is there need to write error log in all functions when vault server error?
    def __init__(self, url='', token='', verify=False, **kwargs):
        self.client = hvac.Client(url=url, token=token, verify=verify)
        if not self.client.is_authenticated():
            error_msg = 'Unable to authenticate to the Vault service'
            logger.error(error_msg)
            raise hvac.exceptions.Unauthorized(error_msg)

    @classmethod
    def get_secret_path(cls, account):
        org = str(account.org_id) or 'default_org'
        ns = str(account.namespace_id) or 'default_namespace'
        path = os.path.join(org, ns, str(account.id))
        return path

    def get_metadata(self, account):
        path = self.get_secret_path(account)
        meta_data = self.client.secrets.kv.v2.read_secret_metadata(
            mount_point=self.engine, path=path
        ).get('data')
        return meta_data

    def get_secret(self, account, version=None):
        path = self.get_secret_path(account)
        key = self.client.secrets.kv.v2.read_secret_version(
            mount_point=self.engine, path=path, version=version
        ).get('data').get('data').get(self.key)
        return key

    def create_secret(self, account, data):
        """secret_data should be a k/v dict"""
        path = self.get_secret_path(account)
        key = self.client.secrets.kv.v2.create_or_update_secret(
            mount_point=self.engine, path=path, secret=data
        )
        return key

    def update_secret(self, account, data):
        old_secret = self.get_secret(account)
        if old_secret != data.get(self.key):
            path = self.get_secret_path(account)
            key = self.client.secrets.kv.v2.create_or_update_secret(
                mount_point=self.engine, path=path, secret=data
            )
            return key

    def delete_secret(self, account):
        path = self.get_secret_path(account)
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            mount_point=self.engine, path=path
        )
