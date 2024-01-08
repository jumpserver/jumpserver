# -*- coding: utf-8 -*-
#
import os

from ..const import PROJECT_DIR, CONFIG

LOG_DIR = os.path.join(PROJECT_DIR, 'data', 'logs')
JUMPSERVER_LOG_FILE = os.path.join(LOG_DIR, 'jumpserver.log')
DRF_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'drf_exception.log')
UNEXPECTED_EXCEPTION_LOG_FILE = os.path.join(LOG_DIR, 'unexpected_exception.log')
ANSIBLE_LOG_FILE = os.path.join(LOG_DIR, 'ansible.log')
GUNICORN_LOG_FILE = os.path.join(LOG_DIR, 'gunicorn.log')
LOG_LEVEL = CONFIG.LOG_LEVEL

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
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
            'class': 'logging.handlers.RotatingFileHandler',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 7,
            'formatter': 'main',
            'filename': JUMPSERVER_LOG_FILE,
        },
        'ansible_logs': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'main',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 7,
            'filename': ANSIBLE_LOG_FILE,
        },
        'drf_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'exception',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 7,
            'filename': DRF_EXCEPTION_LOG_FILE,
        },
        'unexpected_exception': {
            'encoding': 'utf8',
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'exception',
            'maxBytes': 1024 * 1024 * 100,
            'backupCount': 7,
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
        'ops.ansible_api': {
            'handlers': ['console', 'ansible_logs'],
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
        }
    }
}

SYSLOG_ENABLE = CONFIG.SYSLOG_ENABLE

if CONFIG.SYSLOG_ADDR != '' and len(CONFIG.SYSLOG_ADDR.split(':')) == 2:
    host, port = CONFIG.SYSLOG_ADDR.split(':')
    LOGGING['handlers']['syslog'].update({
        'class': 'logging.handlers.SysLogHandler',
        'facility': CONFIG.SYSLOG_FACILITY,
        'address': (host, int(port)),
        'socktype': CONFIG.SYSLOG_SOCKTYPE,
    })

if not os.path.isdir(LOG_DIR):
    os.makedirs(LOG_DIR, mode=0o755)
