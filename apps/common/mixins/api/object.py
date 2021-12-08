# -*- coding: utf-8 -*-
#

from secret.backends.endpoint import Secret

__all__ = ['GetObjectMixin']


class GetObjectMixin:
    """ 重写get_object方法 替换实例中的密钥信息 """

    def get_object(self):
        obj = super().get_object()
        if Secret.is_allow(obj, is_instance=True):
            obj.replace_secret()
        return obj
