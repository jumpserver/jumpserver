# -*- coding: utf-8 -*-
#
import hvac
from hvac import exceptions
from requests.exceptions import ConnectionError

from common.utils import get_logger

logger = get_logger(__name__)

__all__ = ['VaultKVClient']


class VaultKVClient(object):
    max_versions = 20

    def __init__(self, url, token, mount_point):
        assert isinstance(self.max_versions, int) and self.max_versions >= 3, (
            'max_versions must to be an integer that is greater than or equal to 3'
        )
        self.client = hvac.Client(url=url, token=token)
        self.mount_point = mount_point
        self.enable_secrets_engine_if_need()

    def is_active(self):
        try:
            if not self.client.sys.is_initialized():
                return False, 'Vault is not initialized'
            if self.client.sys.is_sealed():
                return False, 'Vault is sealed'
            if not self.client.is_authenticated():
                return False, 'Vault is not authenticated'
        except ConnectionError as e:
            logger.error(str(e))
            return False, f'Vault is not reachable: {e}'
        else:
            return True, ''

    def enable_secrets_engine_if_need(self):
        secrets_engines = self.client.sys.list_mounted_secrets_engines()
        mount_points = secrets_engines.keys()
        if f'{self.mount_point}/' in mount_points:
            return
        self.client.sys.enable_secrets_engine(
            backend_type='kv',
            path=self.mount_point,
            options={'version': 2}  # TODO: version 是否从配置中读取?
        )
        self.client.secrets.kv.v2.configure(
            max_versions=self.max_versions,
            mount_point=self.mount_point
        )

    def get(self, path, version=None):
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                version=version,
                mount_point=self.mount_point
            )
        except exceptions.InvalidPath as e:
            return {}
        data = response.get('data', {})
        return data

    def create(self, path, data: dict):
        self._update_or_create(path=path, data=data)

    def update(self, path, data: dict):
        """ 未更新的数据会被删除 """
        self._update_or_create(path=path, data=data)

    def patch(self, path, data: dict):
        """ 未更新的数据不会被删除 """
        self.client.secrets.kv.v2.patch(
            path=path,
            secret=data,
            mount_point=self.mount_point
        )

    def delete(self, path):
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path,
            mount_point=self.mount_point,
        )

    def _update_or_create(self, path, data: dict):
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path,
            secret=data,
            mount_point=self.mount_point
        )

    def update_metadata(self, path, metadata: dict):
        try:
            self.client.secrets.kv.v2.update_metadata(
                path=path,
                mount_point=self.mount_point,
                custom_metadata=metadata
            )
        except exceptions.InvalidPath as e:
            logger.error('Update metadata error: {}'.format(e))
