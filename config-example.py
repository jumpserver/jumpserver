"""
    jumpserver.config
    ~~~~~~~~~~~~~~~~~

    Jumpserver project setting file

    :copyright: (c) 2014-2016 by Jumpserver Team.
    :license: GPL v2, see LICENSE for more details.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'
    DISPLAY_PER_PAGE = 20
    SITE_URL = 'http://m'
    ALLOWED_HOSTS = ['*']
    DEBUG = False
    LOG_LEVEL = 'DEBUG'
    DATABASE_ENGINE = 'sqlite3'
    HTTP_LISTEN_HOST = '127.0.0.1'
    HTTP_LISTEN_PORT = 8000
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_PASSWORD = ''
    EMAIL_HOST = ''
    EMAIL_PORT = 25
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''
    EMAIL_USE_SSL = False  # If port is 465, set True
    EMAIL_USE_TLS = False  # If port is 587, set True
    EMAIL_SUBJECT_PREFIX = '[Jumpserver] '

    def __init__(self):
        pass

    def __getattr__(self, item):
        return None


class DevelopmentConfig(Config):
    DEBUG = True
    DISPLAY_PER_PAGE = 20
    DB_ENGINE = 'sqlite'
    DB_NAME = os.path.join(BASE_DIR, 'db.sqlite3')


class ProductionConfig(Config):
    DEBUG = False
    DB_ENGINE = 'mysql'
    DB_HOST = '127.0.0.1'
    DB_PORT = 3306
    DB_USER = 'root'
    DB_PASSWORD = ''
    DB_NAME = 'jumpserver'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,

    'default': DevelopmentConfig,
}

env = 'development'
