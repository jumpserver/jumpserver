# -*- coding: utf-8 -*-
#

from .base import BaseBackend

from .external.utils import get_backend
from .internal.asset_user import AssetUserBackend


class AssetUserManager(BaseBackend):
    """
    资产用户管理器
    """
    external_backend = get_backend()
    internal_backend = AssetUserBackend

    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        external_instance = list(cls.external_backend.filter(username, asset))
        internal_instance = list(cls.internal_backend.filter(username, asset))
        instances = cls._merge_instances(external_instance, internal_instance)
        return instances

    @classmethod
    def create(cls, **kwargs):
        instance = cls.external_backend.create(**kwargs)
        return instance

    @classmethod
    def _merge_instances(cls, external_instances, internal_instances):
        external_instances_keyword_list = [
            {'username': instance.username, 'asset': instance.asset}
            for instance in external_instances
        ]
        instances = [
            instance for instance in internal_instances
            if instance.keyword not in external_instances_keyword_list
        ]
        external_instances.extend(instances)
        return external_instances
