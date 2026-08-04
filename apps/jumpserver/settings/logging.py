# -*- coding: utf-8 -*-
#
import os

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
            'format': 'jumpserver: %(message)s'
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
            'handlers': ['console', 'file', 'syslog'],
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

# 仅从 django.conf.settings 读取（通过界面 / API 配置），
# 未配置时使用硬编码默认值
_syslog_addr = getattr(settings, 'SYSLOG_ADDR', '')
_syslog_facility = getattr(settings, 'SYSLOG_FACILITY', 'user')
_syslog_socktype = getattr(settings, 'SYSLOG_SOCKTYPE', 2)

if _syslog_addr != '' and len(_syslog_addr.split(':')) == 2:
    host, port = _syslog_addr.split(':')
    LOGGING['handlers']['syslog'].update({
        'class': 'logging.handlers.SysLogHandler',
        'facility': _syslog_facility,
        'address': (host, int(port)),
        'socktype': _syslog_socktype,
    })

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR, mode=0o755)


def _get_syslog_config():
    """获取当前 syslog 配置（仅从 django.conf.settings，由界面 / API 管理）"""
    addr = getattr(settings, 'SYSLOG_ADDR', '')
    facility = getattr(settings, 'SYSLOG_FACILITY', 'user')
    socktype = getattr(settings, 'SYSLOG_SOCKTYPE', 2)
    return addr, facility, socktype


def _is_valid_addr(addr):
    """检查 syslog 地址是否合法（host:port 格式）"""
    if not addr:
        return False
    parts = addr.split(':')
    if len(parts) != 2:
        return False
    try:
        int(parts[1])
        return True
    except ValueError:
        return False


SYSLOG_LOGGER_NAMES = ('django.request', 'django.server', 'syslog')


def reconfigure_syslog_handler():
    """动态重载 syslog handler，支持 API 修改后不重启生效"""
    addr, facility, socktype = _get_syslog_config()

    if _is_valid_addr(addr):
        host, port = addr.split(':')
        LOGGING['handlers']['syslog'].update({
        'class': 'logging.handlers.SysLogHandler',
        'facility': facility,
        'address': (host, int(port)),
        'socktype': socktype,
    })
    else:
        LOGGING['handlers']['syslog']['class'] = 'logging.NullHandler'

