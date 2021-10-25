# coding: utf-8
from jumpserver.context_processor import default_interface
from django.conf import settings


class ObjectDict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)


def get_interface_setting():
    if not settings.XPACK_ENABLED:
        return default_interface
    from xpack.plugins.interface.models import Interface
    return Interface.get_interface_setting()


def get_login_title():
    return get_interface_setting()['login_title']
