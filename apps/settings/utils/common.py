# coding: utf-8
from jumpserver.context_processor import default_interface
from django.conf import settings


def get_interface_setting_or_default():
    if not settings.XPACK_ENABLED:
        return default_interface
    from xpack.plugins.interface.models import Interface
    return Interface.get_interface_setting()


def get_login_title():
    return get_interface_setting_or_default()['login_title']
