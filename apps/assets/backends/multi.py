# -*- coding: utf-8 -*-
#
import uuid

from .base import BaseBackend
from .external import AuthBookBackend
from .internal import SystemUserBackend, AdminUserBackend


class AssetUserQuerySet(list):
    def order_by(self, *ordering):
        _ordering = []
        reverse = False
        for i in ordering:
            if i[0] == '-':
                reverse = True
                i = i[1:]
            _ordering.append(i)
        self.sort(key=lambda obj: [getattr(obj, j) for j in _ordering], reverse=reverse)
        return self

    def filter(self, **kwargs):
        id_in = kwargs.pop('id__in', None)

        def filter_it(obj):
            wanted = []
            real = []
            for k, v in kwargs.items():
                wanted.append(v)
                value = getattr(obj, k)
                if isinstance(value, uuid.UUID):
                    value = str(value)
                real.append(value)
            return wanted == real

        queryset = AssetUserQuerySet([i for i in self if filter_it(i)])
        if id_in:
            queryset = AssetUserQuerySet([i for i in queryset if str(i.id) in id_in])
        return queryset

    def __or__(self, other):
        self.extend(other)
        return self


class AssetUserManager(BaseBackend):
    """
    资产用户管理器
    """
    backends = (
        ('db', AuthBookBackend),
        ('system_user', SystemUserBackend),
        ('admin_user', AdminUserBackend),
    )

    @classmethod
    def filter(cls, username=None, asset=None, latest=True, prefer="system_user"):
        instances_map = {}
        instances = []
        for name, backend in cls.backends:
            instances_map[name] = backend.filter(
                username=username, asset=asset, latest=latest
            )

        # 如果不是获取最新版本，就不再merge
        if not latest:
            for _instances in instances_map.values():
                instances.extend(_instances)
            return instances

        # merge的顺序
        ordering = ["db"]
        if prefer == "system_user":
            ordering.extend(["system_user", "admin_user"])
        else:
            ordering.extend(["admin_user", "system_user"])
        ordering_instances = [instances_map.get(i) for i in ordering]
        instances = cls._merge_instances(*ordering_instances)
        return AssetUserQuerySet(instances)

    @classmethod
    def create(cls, **kwargs):
        instance = AuthBookBackend.create(**kwargs)
        return instance

    @classmethod
    def filter_by_node(cls, node):
        assets = node.get_all_assets()
        all_instances = AssetUserQuerySet()
        for asset in assets:
            instances = cls.filter(asset=asset)
            all_instances.extend(instances)
        return all_instances

    @classmethod
    def all(cls):
        return cls.filter()

    @classmethod
    def _merge_instances(cls, *args):
        instances = list(args[0])
        keywords = [obj.keyword for obj in instances]

        for _instances in args[1:]:
            need_merge_instances = [obj for obj in _instances if obj.keyword not in keywords]
            need_merge_keywords = [obj.keyword for obj in need_merge_instances]
            instances.extend(need_merge_instances)
            keywords.extend(need_merge_keywords)
        return instances
