# -*- coding: utf-8 -*-
#
import uuid
from abc import abstractmethod

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist


class NotSupportError(Exception):
    pass


class BaseBackend:
    ObjectDoesNotExist = ObjectDoesNotExist
    MultipleObjectsReturned = MultipleObjectsReturned
    NotSupportError = NotSupportError
    MSG_NOT_EXIST = '{} Object matching query does not exist'
    MSG_MULTIPLE = '{} get() returned more than one object ' \
                   '-- it returned {}!'

    @classmethod
    def get(cls, username, asset):
        instances = cls.filter(username, assets=[asset])
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            cls.raise_does_not_exist(cls.__name__)
        else:
            cls.raise_multiple_return(cls.__name__, len(instances))

    @classmethod
    @abstractmethod
    def filter(cls, username=None, assets=None, latest=True):
        """
        :param username: 用户名
        :param assets: <Asset>对象
        :param latest: 是否是最新记录
        :return: 元素为<AuthBook>的可迭代对象(<list> or <QuerySet>)
        """
        pass

    @classmethod
    @abstractmethod
    def create(cls, **kwargs):
        """
        :param kwargs:
        {
            name, username, asset, comment, password, public_key, private_key,
            (org_id)
        }
        :return: <AuthBook>对象
        """
        pass

    @classmethod
    def raise_does_not_exist(cls, name):
        raise cls.ObjectDoesNotExist(cls.MSG_NOT_EXIST.format(name))

    @classmethod
    def raise_multiple_return(cls, name, length):
        raise cls.MultipleObjectsReturned(cls.MSG_MULTIPLE.format(name, length))


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
                in_kwargs[k] = v
        for k in in_kwargs:
            kwargs.pop(k)

        if len(in_kwargs) == 0:
            return self
        for i in self:
            matched = True
            for k, v in in_kwargs.items():
                key = k.split('__')[0]
                attr = getattr(i, key, None)
                # 如果属性或者value中是uuid,则转换成string
                if isinstance(v[0], uuid.UUID):
                    v = [str(i) for i in v]
                if isinstance(attr, uuid.UUID):
                    attr = str(attr)
                if attr not in v:
                    matched = False
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

    def __or__(self, other):
        self.extend(other)
        return self
