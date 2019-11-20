# -*- coding: utf-8 -*-
#
import uuid
from abc import abstractmethod


class BaseBackend:
    @classmethod
    @abstractmethod
    def filter(cls, username=None, assets=None, latest=True, prefer=None, prefer_id=None):
        """
        :param username: 用户名
        :param assets: <Asset>对象
        :param latest: 是否是最新记录
        :param prefer: 优先使用
        :param prefer_id: 使用id
        :return: 元素为<AuthBook>的可迭代对象(<list> or <QuerySet>)
        """
        pass


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

    def filter_in(self, kwargs):
        in_kwargs = {}
        queryset = []
        for k, v in kwargs.items():
            if len(v) == 0:
                return self
            if k.find("__in") >= 0:
                _k = k.split('__')[0]
                in_kwargs[_k] = v
            else:
                in_kwargs[k] = v
        for k in in_kwargs:
            kwargs.pop(k)

        if len(in_kwargs) == 0:
            return self
        for i in self:
            matched = False
            for k, v in in_kwargs.items():
                attr = getattr(i, k, None)
                # 如果属性或者value中是uuid,则转换成string
                if isinstance(v[0], uuid.UUID):
                    v = [str(i) for i in v]
                if isinstance(attr, uuid.UUID):
                    attr = str(attr)
                if v in attr:
                    matched = True
            if matched:
                queryset.append(i)
        return AssetUserQuerySet(queryset)

    def filter_equal(self, kwargs):
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
        if len(kwargs) > 0:
            queryset = AssetUserQuerySet([i for i in self if filter_it(i)])
        else:
            queryset = self
        return queryset

    def filter(self, **kwargs):
        queryset = self.filter_in(kwargs).filter_equal(kwargs)
        return queryset

    def distinct(self):
        items = list(set(self))
        self[:] = items
        return self

    def __or__(self, other):
        self.extend(other)
        return self
