# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from .backends import meta
from .backends.external import backend as external_backend
from .backends.internal import backend as internal_backend


class AssetUserManager:
    """
    资产用户管理器
    """

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
        external_instance = list(external_backend.filter(username, asset))
        internal_instance = list(internal_backend.filter(username, asset))
        instances = cls._merge_instances(external_instance, internal_instance)
        return instances

    @classmethod
    def create(cls, **kwargs):
        instance = external_backend.create(**kwargs)
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
