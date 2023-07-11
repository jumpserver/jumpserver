# -*- coding: utf-8 -*-
#
from collections.abc import Iterable

from hvac import exceptions

from common.utils import get_logger
from .base import BaseVault

__all__ = ['VaultKVEngine']

logger = get_logger(__name__)


class VaultKVEngine(BaseVault):
    _mount_points = set()

    def __init__(self, mount_point, url, token):
        super().__init__(url=url, token=token)
        max_versions = 20
        assert isinstance(max_versions, int) and 3 <= max_versions, (
            'max_versions must to be an integer that is greater than or equal to 3'
        )
        self.mount_point = mount_point
        self.max_versions = max_versions
        self.enable_secrets_engine()

    @property
    def mount_points(self):
        return self.__class__._mount_points

    @mount_points.setter
    def mount_points(self, value: Iterable):
        # 只操作字符串和可迭代对象，添加到类属性_mount_points中
        mount_points = type(self)._mount_points
        mount_points.update(value)

    def enable_secrets_engine(self):
        mount_point = self.mount_point
        if mount_point in self.mount_points:
            return

        secrets_engines = self.client.sys.list_mounted_secrets_engines()
        mount_points = secrets_engines.keys()
        if f'{mount_point}/' in mount_points:
            self.mount_points = {i.rstrip('/') for i in mount_points}
            return

        self.client.sys.enable_secrets_engine(
            backend_type='kv',
            path=mount_point,
            options={'version': 2}
        )

        self.client.secrets.kv.v2.configure(
            max_versions=self.max_versions,
            mount_point=mount_point
        )
        self.mount_points = {mount_point}

    def get(self, path, version=None):
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=path, version=version, mount_point=self.mount_point
            )
            data = response.get('data', {})
        except exceptions.InvalidPath as e:
            logger.error('Read secret error: {} -> {}'.format(path, str(e)))
            data = {}
        return data

    def patch(self, path, data: dict):
        """ 未更新的数据不会被删除 """
        try:
            self.client.secrets.kv.v2.patch(
                path=path, secret=data, mount_point=self.mount_point
            )
        except exceptions.InvalidPath as e:
            logger.error('Patch secret error: {}'.format(e))

    def _update_or_create(self, path, data: dict):
        self.client.secrets.kv.v2.create_or_update_secret(
            path=path, secret=data, mount_point=self.mount_point
        )

    def create(self, path, data: dict):
        self._update_or_create(path=path, data=data)

    def update(self, path, data: dict):
        """ 未更新的数据会被删除 """
        self._update_or_create(path=path, data=data)

    def delete(self, path):
        self.client.secrets.kv.v2.delete_metadata_and_all_versions(
            path=path, mount_point=self.mount_point,
        )

    def update_metadata(self, path, metadata: dict):
        try:
            self.client.secrets.kv.v2.update_metadata(
                path=path, mount_point=self.mount_point, custom_metadata=metadata
            )
        except exceptions.InvalidPath as e:
            logger.error('Update metadata error: {}'.format(e))
