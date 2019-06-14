# -*- coding: utf-8 -*-
#
from .base import AssetUserQuerySet, BaseBackend
from .db import AuthBookBackend
from .system_user import SystemUserBackend
from .admin_user import AdminUserBackend


class AssetUserManager(BaseBackend):
    """
    资产用户管理器
    """
    backends = (
        ('db', AuthBookBackend),
        ('system_user', SystemUserBackend),
        ('admin_user', AdminUserBackend),
    )

    _prefer = "system_user"
    _using = None

    def filter(self, username=None, assets=None, latest=True):
        if self._using:
            backend = dict(self.backends).get(self._using)
            if not backend:
                return self.none()
            instances = backend.filter(username=username, assets=assets, latest=latest)
            return AssetUserQuerySet(instances)

        instances_map = {}
        instances = []
        for name, backend in self.backends:
            instances_map[name] = backend.filter(
                username=username, assets=assets, latest=latest
            )

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
        ordering_instances = [instances_map.get(i) for i in ordering]
        instances = self._merge_instances(*ordering_instances)
        return AssetUserQuerySet(instances)

    @staticmethod
    def create(**kwargs):
        instance = AuthBookBackend.create(**kwargs)
        return instance

    def all(self):
        return self.filter()

    def prefer(self, s):
        self._prefer = s
        return self

    def using(self, s):
        self._using = s
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
