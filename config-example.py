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
    # Use it to encrypt or decrypt data
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'

    # How many line display every page, default 20
    DISPLAY_PER_PAGE = 20

    # It's used to identify your site, When we send a create mail to user, we only know login url is /login/
    # But we should know the absolute url like: http://jms.jumpserver.org/login/, so SITE_URL is
    # HTTP_PROTOCOL://HOST[:PORT]
    # Todo: May be use :method: get_current_site more  grace, bug restful api unknown ok or not
    SITE_URL = 'http://localhost'

    # Django security setting, if your disable debug model, you should setting that
    ALLOWED_HOSTS = ['*']

    # Development env open this, when error occur display the full process track, Production disable it
    DEBUG = True

    # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
    LOG_LEVEL = 'DEBUG'

    # Database setting, Support sqlite3, mysql, postgres ....
    # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

    # Sqlite setting:
    DATABASE_ENGINE = 'sqlite3'
    DB_NAME = os.path.join(BASE_DIR, 'db.sqlite3')

    # Mysql or postgres setting like:
    # DB_ENGINE = 'mysql'
    # DB_HOST = '127.0.0.1'
    # DB_PORT = 3306
    # DB_USER = 'root'
    # DB_PASSWORD = ''
    # DB_NAME = 'jumpserver'

    # When Django start it will bind this host and port
    # ./manage.py runserver 127.0.0.1:8080
    # Todo: Gunicorn or uwsgi run may be use it
    HTTP_LISTEN_HOST = '0.0.0.0'
    HTTP_LISTEN_PORT = 8080

    # Use Redis as broker for celery and web socket
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    # REDIS_PASSWORD = ''

    # Email SMTP setting, we only support smtp send mail
    # EMAIL_HOST = 'smtp.qq.com'
    # EMAIL_PORT = 25
    # EMAIL_HOST_USER = ''
    # EMAIL_HOST_PASSWORD = ''
    # EMAIL_USE_SSL = False  # If port is 465, set True
    # EMAIL_USE_TLS = False  # If port is 587, set True
    # EMAIL_SUBJECT_PREFIX = '[Jumpserver] '

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
