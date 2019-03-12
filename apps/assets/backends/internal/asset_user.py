# -*- coding: utf-8 -*-
#

from ..base import BaseBackend
from .admin_user import AdminUserBackend
from .system_user import SystemUserBackend


class AssetUserBackend(BaseBackend):
    @classmethod
    def filter(cls, username=None, asset=None, **kwargs):
        admin_user_instances = AdminUserBackend.filter(username, asset)
        system_user_instances = SystemUserBackend.filter(username, asset)
        instances = cls._merge_instances(admin_user_instances, system_user_instances)
        return instances

    @classmethod
    def _merge_instances(cls, admin_user_instances, system_user_instances):
        admin_user_instances_keyword_list = [
            {'username': instance.username, 'asset': instance.asset}
            for instance in admin_user_instances
        ]
        instances = [
            instance for instance in system_user_instances
            if instance.keyword not in admin_user_instances_keyword_list
        ]
        admin_user_instances.extend(instances)
        return admin_user_instances

    @classmethod
    def create(cls, **kwargs):
        raise cls.NotSupportError("Not support create")
