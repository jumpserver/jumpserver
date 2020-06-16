# -*- coding: utf-8 -*-
#
import os

from werkzeug.local import LocalProxy

from .conf import ConfigManager
from common.local import thread_local

__all__ = ['BASE_DIR', 'PROJECT_DIR', 'VERSION', 'CONFIG', 'DYNAMIC', 'LOCAL_DYNAMIC_SETTINGS']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
VERSION = '2.0.0'
CONFIG = ConfigManager.load_user_config()
DYNAMIC = ConfigManager.get_dynamic_config(CONFIG)


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
