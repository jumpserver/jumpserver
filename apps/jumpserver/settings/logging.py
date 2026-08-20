# -*- coding: utf-8 -*-
#
import logging
import os
from logging.handlers import SysLogHandler

from django.conf import settings

from ..const import PROJECT_DIR, CONFIG

LOG_DIR = os.path.join(PROJECT_DIR, 'data', 'logs')
JUMPSERVER_LOG_FILE = os.path.join(LOG_DIR, 'jumpserver.log')
DRF_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'drf_exception.log')
UNEXPECTED_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'unexpected_exception.log')
GUNICORN_LOG_FILE = os.path.join(LOG_DIR, 'gunicorn.log')
LOG_LEVEL = CONFIG.LOG_LEVEL

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(pathname)s:%(lineno)d  %(message)s'
        },
        'main': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': '%(asctime)s [%(levelname).4s] %(message)s',
        },
        'exception': {
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'format': '\n%(asctime)s [%(levelname)s] %(message)s',
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'syslog': {
            'format': 'osm: %(message)s'
        },
        'msg': {
            'format': '%(message)s'
        }
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'main'
        },
        'file': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'main',
            'filename': JUMPSERVER_LOG_FILE,
        },
        'drf_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'exception',
            'filename': DRF_EXCEPTION_LOG_FILE,
        },
        'unexpected_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'jumpserver.rewriting.logging.DailyTimedRotatingFileHandler',
            'when': 'midnight',
            'formatter': 'exception',
            'filename': UNEXPECTED_EXCEPTION_LOG_FILE,
        },
        'syslog': {
            'level': 'INFO',
            'class': 'logging.NullHandler',
            'formatter': 'syslog'
        },
    },
    'loggers': {
        'django': {
            'handlers': ['null'],
            'propagate': False,
            'level': LOG_LEVEL,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console', 'file', 'syslog'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'jumpserver': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
        'drf_exception': {
            'handlers': ['console', 'drf_exception'],
            'level': LOG_LEVEL,
        },
        'unexpected_exception': {
            'handlers': ['unexpected_exception'],
            'level': LOG_LEVEL,
        },
        'django_auth_ldap': {
            'handlers': ['console', 'file'],
            'level': "INFO",
        },
        'syslog': {
            'handlers': ['syslog'],
            'level': 'INFO'
        },
        'azure': {
            'handlers': ['null'],
            'level': 'ERROR'
        },
        'oauth2_provider': {
            'handlers': ['console', 'file'],
            'level': LOG_LEVEL,
        },
    }
}

if CONFIG.DEBUG_DEV:
    LOGGING['loggers']['django.db'] = {
        'handlers': ['console', 'file'],
        'level': 'DEBUG'
    }

SYSLOG_ENABLE = CONFIG.SYSLOG_ENABLE

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR, mode=0o755)


def _get_syslog_config():
    """获取当前 syslog 配置（仅从 django.conf.settings，由界面 / API 管理）"""
    enabled = getattr(settings, 'SYSLOG_ENABLE', False)
    host = getattr(settings, 'SYSLOG_HOST', '')
    port = getattr(settings, 'SYSLOG_PORT', 514)
    facility = getattr(settings, 'SYSLOG_FACILITY', 'user')
    socktype = getattr(settings, 'SYSLOG_SOCKTYPE', 2)
    return enabled, host, port, facility, socktype


def _is_valid_host(host):
    """检查 syslog 主机是否合法（非空）"""
    return bool(host)

# 'django.server', 
SYSLOG_LOGGER_NAMES = ('syslog',)


def reconfigure_syslog_handler():
    """动态重载 syslog handler，支持 API 修改后不重启生效"""
    enabled, host, port, facility, socktype = _get_syslog_config()
    if enabled and _is_valid_host(host):
        handler = SysLogHandler(
            address=(host, int(port)),
            facility=facility,
            socktype=socktype,
        )
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter('osm: %(message)s'))
    else:
        handler = logging.NullHandler()

    to_close = set()
    for logger_name in SYSLOG_LOGGER_NAMES:
        logger = logging.getLogger(logger_name)
        for h in list(logger.handlers):
            if h.__class__.__name__ in ('SysLogHandler', 'NullHandler'):
                logger.removeHandler(h)
                to_close.add(h)
        logger.addHandler(handler)

    for h in to_close:
        try:
            h.close()
        except Exception:
            pass
