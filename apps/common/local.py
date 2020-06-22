# -*- coding: utf-8 -*-
#
from jumpserver.const import DYNAMIC
from werkzeug.local import Local, LocalProxy

thread_local = Local()


def _find(attr):
    return getattr(thread_local, attr, None)


class _Settings:
    pass


def get_dynamic_cfg_from_thread_local():
    KEY = 'dynamic_config'

    try:
        cfg = getattr(thread_local, KEY)
    except AttributeError:
        cfg = _Settings()
        setattr(thread_local, KEY, cfg)

    return cfg


class DynamicDefaultLocalProxy(LocalProxy):
    def __getattr__(self, item):
        try:
            value = super().__getattr__(item)
        except AttributeError:
            value = getattr(DYNAMIC, item)()
            setattr(self, item, value)

        return value


LOCAL_DYNAMIC_SETTINGS = DynamicDefaultLocalProxy(get_dynamic_cfg_from_thread_local)
