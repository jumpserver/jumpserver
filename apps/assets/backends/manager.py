# -*- coding: utf-8 -*-
#
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist

from .base import AssetUserQuerySet
from .db import AuthBookBackend
from .system_user import SystemUserBackend
from .admin_user import AdminUserBackend


class NotSupportError(Exception):
    pass


class AssetUserManager:
    """
    资产用户管理器
    """
    ObjectDoesNotExist = ObjectDoesNotExist
    MultipleObjectsReturned = MultipleObjectsReturned
    NotSupportError = NotSupportError
    MSG_NOT_EXIST = '{} Object matching query does not exist'
    MSG_MULTIPLE = '{} get() returned more than one object ' \
                   '-- it returned {}!'

    backends = (
        ('db', AuthBookBackend),
        ('system_user', SystemUserBackend),
        ('admin_user', AdminUserBackend),
    )

    _prefer = "system_user"

    def filter(self, username=None, assets=None, latest=True, prefer=None, prefer_id=None):
        if assets is not None and not assets:
            return AssetUserQuerySet([])

        if prefer:
            self._prefer = prefer

        instances_map = {}
        instances = []
        for name, backend in self.backends:
            # if name != "db":
            #     continue
            _instances = backend.filter(
                username=username, assets=assets, latest=latest,
                prefer=self._prefer, prefer_id=prefer_id,
            )
            instances_map[name] = _instances

        # 如果不是获取最新版本，就不再merge
        if not latest:
            for _instances in instances_map.values():
                instances.extend(_instances)
            return AssetUserQuerySet(instances)

        # merge的顺序
        ordering = ["db"]
        if self._prefer == "system_user":
            ordering.extend(["system_user", "admin_user"])
        else:
            ordering.extend(["admin_user", "system_user"])
        # 根据prefer决定优先使用系统用户或管理用户谁的
        ordering_instances = [instances_map.get(i, []) for i in ordering]
        instances = self._merge_instances(*ordering_instances)
        return AssetUserQuerySet(instances)

    def get(self, username, asset, **kwargs):
        instances = self.filter(username, assets=[asset], **kwargs)
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            self.raise_does_not_exist(self.__class__.__name__)
        else:
            self.raise_multiple_return(self.__class__.__name__, len(instances))

    def raise_does_not_exist(self, name):
        raise self.ObjectDoesNotExist(self.MSG_NOT_EXIST.format(name))

    def raise_multiple_return(self, name, length):
        raise self.MultipleObjectsReturned(self.MSG_MULTIPLE.format(name, length))

    @staticmethod
    def create(**kwargs):
        instance = AuthBookBackend.create(**kwargs)
        return instance

    def all(self):
        return self.filter()

    def prefer(self, s):
        self._prefer = s
        return self

    @staticmethod
    def none():
        return AssetUserQuerySet()

    @staticmethod
    def _merge_instances(*args):
        instances = list(args[0])
        keywords = [obj.keyword for obj in instances]

        for _instances in args[1:]:
            need_merge_instances = [obj for obj in _instances if obj.keyword not in keywords]
            need_merge_keywords = [obj.keyword for obj in need_merge_instances]
            instances.extend(need_merge_instances)
            keywords.extend(need_merge_keywords)
        return instances
