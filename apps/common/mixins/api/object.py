# -*- coding: utf-8 -*-
#

from assets.models import BaseUser

__all__ = ['GetObjectMixin']


class GetObjectMixin:
    """ 重写get_object方法 替换实例中的密钥信息 """

    def get_object(self):
        obj = super().get_object()
        if isinstance(obj, BaseUser):
            obj.replace_secret()
        return obj
