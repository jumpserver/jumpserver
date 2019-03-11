# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from .. import meta
from .admin_user import AdminUserBackend
from .system_user import SystemUserBackend


class AssetUserBackend:

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, asset)
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            msg = meta.EXCEPTION_MSG_NOT_EXIST.format(cls.__name__)
            raise ObjectDoesNotExist(msg)
        else:
            msg = meta.EXCEPTION_MSG_MULTIPLE.format(cls.__name__, len(instances))
            raise MultipleObjectsReturned(msg)

    @classmethod
    def filter(cls, username=None, asset=None):
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
