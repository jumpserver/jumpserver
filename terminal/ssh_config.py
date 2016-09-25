#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import os


BASE_DIR = os.path.dirname(os.path.abspath(__name__))


class Config:
    SSH_HOST = ''
    SSH_PORT = 2200
    LOG_LEVEL = 'INFO'
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_FILENAME = 'ssh_server.log'
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
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
                'formatter': 'main',
                'stream': 'ext://sys.stdout',
            },
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'formatter': 'main',
                'mode': 'a',
                'filename': os.path.join(LOG_DIR, LOG_FILENAME),
            },
        },
        'loggers': {
            'jumpserver': {
                'handlers': ['console', 'file'],
                # 'level': LOG_LEVEL_CHOICES.get(LOG_LEVEL, None) or LOG_LEVEL_CHOICES.get('info')
                'level': LOG_LEVEL,
                'propagate': True,
            },
            'jumpserver.web_ssh_server': {
                'handlers': ['console', 'file'],
                # 'level': LOG_LEVEL_CHOICES.get(LOG_LEVEL, None) or LOG_LEVEL_CHOICES.get('info')
                'level': LOG_LEVEL,
                'propagate': True,
            },
            'jumpserver.ssh_server': {
                'handlers': ['console', 'file'],
                # 'level': LOG_LEVEL_CHOICES.get(LOG_LEVEL, None) or LOG_LEVEL_CHOICES.get('info')
                'level': LOG_LEVEL,
                'propagate': True,
            }
        }
    }

    def __init__(self):
        pass

    def __getattr__(self, item):
        return None


class DevelopmentConfig(Config):
    pass


class ProductionConfig(Config):
    pass


class TestingConfig(Config):
    pass


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig,
}

env = 'default'


if __name__ == '__main__':
    pass

