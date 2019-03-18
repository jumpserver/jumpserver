# -*- coding: utf-8 -*-
#

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from abc import abstractmethod


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
        instances = cls.filter(username, asset)
        if len(instances) == 1:
            return instances[0]
        elif len(instances) == 0:
            cls.raise_does_not_exist(cls.__name__)
        else:
            cls.raise_multiple_return(cls.__name__, len(instances))

    @classmethod
    @abstractmethod
    def filter(cls, username=None, asset=None, latest=True):
        """
        :param username: 用户名
        :param asset: <Asset>对象
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
