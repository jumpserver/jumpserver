#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
    jumpserver.config
    ~~~~~~~~~~~~~~~~~

    Jumpserver project setting file

    :copyright: (c) 2014-2017 by Jumpserver Team
    :license: GPL v2, see LICENSE for more details.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    """
    Jumpserver Config File
    Jumpserver 配置文件

    Jumpserver use this config for drive django framework running,
    You can set is value or set the same envirment value,
    Jumpserver look for config order: file => env => default

    Jumpserver使用配置来驱动Django框架的运行，
    你可以在该文件中设置，或者设置同样名称的环境变量,
    Jumpserver使用配置的顺序: 文件 => 环境变量 => 默认值
    """
    # SECURITY WARNING: keep the secret key used in production secret!
    # 加密秘钥 生产环境中请修改为随机字符串，请勿外泄
    SECRET_KEY = '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'

    # SECURITY WARNING: keep the bootstrap token used in production secret!
    # 预共享Token coco和guacamole用来注册服务账号，不在使用原来的注册接受机制
    BOOTSTRAP_TOKEN = 'PleaseChangeMe'

    # Development env open this, when error occur display the full process track, Production disable it
    # DEBUG 模式 开启DEBUG后遇到错误时可以看到更多日志
    # DEBUG = True

    # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
    # 日志级别
    # LOG_LEVEL = 'DEBUG'
    # LOG_DIR = os.path.join(BASE_DIR, 'logs')

    # Session expiration setting, Default 24 hour, Also set expired on on browser close
    # 浏览器Session过期时间，默认24小时, 也可以设置浏览器关闭则过期
    # SESSION_COOKIE_AGE = 3600 * 24
    # SESSION_EXPIRE_AT_BROWSER_CLOSE = False

    # Database setting, Support sqlite3, mysql, postgres ....
    # 数据库设置
    # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

    # SQLite setting:
    # 使用单文件sqlite数据库
    # DB_ENGINE = 'sqlite3'
    # DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

    # MySQL or postgres setting like:
    # 使用Mysql作为数据库
    DB_ENGINE = 'mysql'
    DB_HOST = '127.0.0.1'
    DB_PORT = 3306
    DB_USER = 'jumpserver'
    DB_PASSWORD = ''
    DB_NAME = 'jumpserver'

    # When Django start it will bind this host and port
    # ./manage.py runserver 127.0.0.1:8080
    # 运行时绑定端口
    HTTP_BIND_HOST = '0.0.0.0'
    HTTP_LISTEN_PORT = 8080

    # Use Redis as broker for celery and web socket
    # Redis配置
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    # REDIS_PASSWORD = ''
    # REDIS_DB_CELERY = 3
    # REDIS_DB_CACHE = 4

    # Use OpenID authorization
    # 使用OpenID 来进行认证设置
    # BASE_SITE_URL = 'http://localhost:8080'
    # AUTH_OPENID = False  # True or False
    # AUTH_OPENID_SERVER_URL = 'https://openid-auth-server.com/'
    # AUTH_OPENID_REALM_NAME = 'realm-name'
    # AUTH_OPENID_CLIENT_ID = 'client-id'
    # AUTH_OPENID_CLIENT_SECRET = 'client-secret'

    #
    # OTP_VALID_WINDOW = 0

    def __init__(self):
        pass

    def __getattr__(self, item):
        return None


class DevelopmentConfig(Config):
    pass


class TestConfig(Config):
    pass


class ProductionConfig(Config):
    pass


# Default using Config settings, you can write if/else for different env
config = DevelopmentConfig()

