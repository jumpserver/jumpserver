# -*- coding: utf-8 -*-
#

import abc


class BaseBackend:

    @abc.abstractclassmethod
    def get(self, username, asset):
        """
        :param username: 用户名
        :param asset: 资产对象
        :return: AuthBook对象
        """
        pass

    @abc.abstractclassmethod
    def filter(self, username=None, asset=None, latest=True):
        """
        :param username: 用户名
        :param asset: 资产对象
        :param latest: 是否是最新记录
        :return: 元素为AuthBook的可迭代对象(list or queryset)
        """
        pass

    @abc.abstractclassmethod
    def create(self, **kwargs):
        """
        :param kwargs:
        {name, username, asset, password, public_key, private_key, comment}
        :return: AuthBook对象
        """
        pass
