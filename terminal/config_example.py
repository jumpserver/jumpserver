#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import os


BASE_DIR = os.path.dirname(os.path.abspath(__name__))
LOG_LEVEL_CHOICES = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


class Config:
    LOG_LEVEL = ''
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOGGING = {
        'version': 1,
        'formatters': {
            'verbose': {
                'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
            },
            'main': {
                'datefmt': '%Y-%m-%d %H:%M:%S',
                'format': '%(asctime)s [%(module)s %(levelname)s] %(message)s',
            },
            'simple': {
                'format': '%(levelname)s %(message)s'
            },
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
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'formatter': 'main',
                'filename': os.path.join(PROJECT_DIR, 'logs', 'jumpserver.log')
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
                'handlers': ['console', 'file'],
                'level': LOG_LEVEL,
                'propagate': False,
            },
            'jumpserver': {
                'handlers': ['console', 'file'],
                'level': LOG_LEVEL,
            },
            'jumpserver.users.api': {
                'handlers': ['console', 'file'],
                'level': LOG_LEVEL,
            },
            'jumpserver.users.view': {
                'handlers': ['console', 'file'],
                'level': LOG_LEVEL,
            }
        }
    }

    def __init__(self):
        pass

    def __getattr__(self, item):
        return None



if __name__ == '__main__':
    pass
