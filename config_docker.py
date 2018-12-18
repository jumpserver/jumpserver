"""
    jumpserver.config
    ~~~~~~~~~~~~~~~~~

    Jumpserver project setting file

    :copyright: (c) 2014-2017 by Jumpserver Team
    :license: GPL v2, see LICENSE for more details.
"""
import os
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    # Use it to encrypt or decrypt data
    # SECURITY WARNING: keep the secret key used in production secret!
    SECRET_KEY = os.environ.get('SECRET_KEY') or '2vym+ky!997d5kkcc64mnz06y1mmui3lut#(^wd=%s_qj$1%x'

    # How many line display every page if using django pager, default 25
    DISPLAY_PER_PAGE = 25

    # It's used to identify your site, When we send a create mail to user, we only know login url is /login/
    # But we should know the absolute url like: http://jms.jumpserver.org/login/, so SITE_URL is
    # HTTP_PROTOCOL://HOST[:PORT]
    SITE_URL = 'http://localhost'

    # Django security setting, if your disable debug model, you should setting that
    ALLOWED_HOSTS = ['*']

    # Development env open this, when error occur display the full process track, Production disable it
    DEBUG = True

    # DEBUG, INFO, WARNING, ERROR, CRITICAL can set. See https://docs.djangoproject.com/en/1.10/topics/logging/
    LOG_LEVEL = 'DEBUG'
    LOG_DIR = os.path.join(BASE_DIR, 'logs')

    # Database setting, Support sqlite3, mysql, postgres ....
    # See https://docs.djangoproject.com/en/1.10/ref/settings/#databases

    # SQLite setting:
    DB_ENGINE = 'sqlite3'
    DB_NAME = os.path.join(BASE_DIR, 'data', 'db.sqlite3')

    # MySQL or postgres setting like:
    # DB_ENGINE = 'mysql'
    # DB_HOST = '127.0.0.1'
    # DB_PORT = 3306
    # DB_USER = 'root'
    # DB_PASSWORD = ''
    # DB_NAME = 'jumpserver'

    # When Django start it will bind this host and port
    # ./manage.py runserver 127.0.0.1:8080
    HTTP_BIND_HOST = '0.0.0.0'
    HTTP_LISTEN_PORT = 8080

    # Use Redis as broker for celery and web socket
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379
    REDIS_PASSWORD = ''
    BROKER_URL = 'redis://%(password)s%(host)s:%(port)s/3' % {
        'password': REDIS_PASSWORD,
        'host': REDIS_HOST,
        'port': REDIS_PORT,
    }

    # Api token expiration when create, Jumpserver refresh time when request arrive
    TOKEN_EXPIRATION = 3600

    # Session and csrf domain settings
    SESSION_COOKIE_AGE = 3600*24

    # Email SMTP setting, we only support smtp send mail
    EMAIL_HOST = 'smtp.163.com'
    EMAIL_PORT = 25
    EMAIL_HOST_USER = ''
    EMAIL_HOST_PASSWORD = ''  # Caution: Some SMTP server using `Authorization Code` except password
    EMAIL_USE_SSL = True if EMAIL_PORT == 465 else False
    EMAIL_USE_TLS = True if EMAIL_PORT == 587 else False
    EMAIL_SUBJECT_PREFIX = '[Jumpserver] '

    CAPTCHA_TEST_MODE = False

    # You can set jumpserver usage url here, that when user submit wizard redirect to
    USER_GUIDE_URL = ''

    # LDAP Auth settings
    AUTH_LDAP = False
    AUTH_LDAP_SERVER_URI = 'ldap://localhost:389'
    AUTH_LDAP_BIND_DN = 'cn=admin,dc=jumpserver,dc=org'
    AUTH_LDAP_BIND_PASSWORD = ''
    AUTH_LDAP_SEARCH_OU = 'ou=tech,dc=jumpserver,dc=org'
    AUTH_LDAP_SEARCH_FILTER = '(cn=%(user)s)'
    AUTH_LDAP_USER_ATTR_MAP = {
        "username": "cn",
        "name": "sn",
        "email": "mail"
    }
    AUTH_LDAP_START_TLS = False

    #
    # OTP_VALID_WINDOW = 0

    def __init__(self):
        pass

    def __getattr__(self, item):
        return None


class DockerConfig(Config):
    """
    配置文件默认从环境变量里读取，如果没有会使用后面的默认值
    """
    # 用来加密数据的key, 可以修改，但务必保存好这个字符串,丢失它后加密会无法解开
    # SECRET_KEY = "SOME_KEY_NO_ONE_GUESS"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "MD923lkSDi8213kl),3()&^%aM2q1mz;223lkM0o1"
    # 访问的域名, 格式 http[s]://域名[:端口号]
    # SITE_URL = "http://jumpserver.fit2cloud.com"
    SITE_URL = os.environ.get("SITE_URL") or 'http://localhost'
    # 是否开启DEBUG模式
    # DEBUG = True, or DEBUG = False,
    DEBUG = bool(os.environ.get("DEBUG")) if os.environ.get("DEBUG") else False
    # 日志级别, 默认 INFO
    # LOG_LEVEL = WARN
    LOG_LEVEL = os.environ.get("LOG_LEVEL") or "INFO"
    # 使用的数据库类型，支持 SQLite, MySQL, PostgreSQL, Oracle
    # 数据库设置, 如果使用外部的mysql请设置，否则不要改动

    # DB_ENGINE = "oracle" | "postgre" | "mysql" | "sqlite3"
    DB_ENGINE = os.environ.get("DB_ENGINE") or 'mysql'
    # DB_HOST = "192.168.1.1"
    DB_HOST = os.environ.get("DB_HOST") or 'mysql'
    # 端口号
    # DB_PORT = 3306
    DB_PORT = os.environ.get("DB_PORT") or 3306
    # 数据库账号
    # DB_USER = "jumpserver"
    DB_USER = os.environ.get("DB_USER") or 'root'
    # 数据库密码
    # DB_PASSWORD = "db_jumpserver_password"
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or ''
    # 数据库名称
    # DB_NAME = "jumpserver"
    DB_NAME = os.environ.get("DB_NAME") or 'jumpserver'

    # Redis配置，如果不使用外部redis不要改动
    # Redis地址
    # REDIS_HOST = "192.168.1.1"
    REDIS_HOST = os.environ.get("REDIS_HOST") or 'redis'
    # Redis端口号
    # REDIS_PORT = 6380
    REDIS_PORT = os.environ.get("REDIS_PORT") or 6379
    # Redis密码
    # REDIS_PASSWORD = "redis_password"
    REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD") or ''

    # 邮箱SMTP设置, 可以参考各运营商配置文档
    # SMTP服务器地址
    # EMAIL_HOST = 'smtp.qq.com'
    EMAIL_HOST = 'smtp.163.com'
    # SMTP端口号
    # EMAIL_PORT = 465
    EMAIL_PORT = 25
    # SMTP连接邮箱地址
    # EMAIL_HOST_USER = "noreply@jumpserver.org"
    EMAIL_HOST_USER = ''
    # SMTP邮箱的密码, 注意 一些运营商通常要求使用授权码来发SMTP邮件
    EMAIL_HOST_PASSWORD = ''
    # 是否启用SSL, 如果端口号是 465通常设置为True
    # EMAIL_USE_SSL = True
    EMAIL_USE_SSL = True if EMAIL_PORT == 465 else False
    # 是否启用TLS, 如果端口号是 587通常设置为True
    # EMAIL_USE_TLS = True
    EMAIL_USE_TLS = True if EMAIL_PORT == 587 else False
    # 邮件的主题前缀
    EMAIL_SUBJECT_PREFIX = '[Jumpserver] '

    # 认证启用LDAP的设置
    # 是否启用LDAP，默认不启用
    # AUTH_LDAP = True
    AUTH_LDAP = False
    # LDAP的地址
    AUTH_LDAP_SERVER_URI = 'ldap://localhost:389'
    # LDAP绑定的查询账户
    AUTH_LDAP_BIND_DN = 'cn=admin,dc=jumpserver,dc=org'
    # 密码
    AUTH_LDAP_BIND_PASSWORD = ''
    # 用户所在的ou
    AUTH_LDAP_SEARCH_OU = 'ou=tech,dc=jumpserver,dc=org'
    # 查询时使用的过滤器, 仅可以修改前面的表示符，可能是cn或uid, 也就是登录用户名所在字段
    # AUTH_LDAP_SEARCH_FILTER = '(uid=%(user)s)'
    AUTH_LDAP_SEARCH_FILTER = '(cn=%(user)s)'
    # LDAP用户信息映射到Jumpserver
    AUTH_LDAP_USER_ATTR_MAP = {
        "username": "cn",  # 将LDAP信息中的 `cn` 字段映射为 `username(用户名)`
        "name": "sn",  # 将 LDAP信息中的  `sn` 映射为 `name(姓名)`
        "email": "mail"  # 将 LDAP信息中的 `mail` 映射为 `email(邮箱地址)`
    }
    # 是否启用TLS加密
    AUTH_LDAP_START_TLS = False


    #
    OTP_VALID_WINDOW = int(os.environ.get("OTP_VALID_WINDOW")) if os.environ.get("OTP_VALID_WINDOW") else 0


# Default using Config settings, you can write if/else for different env
config = DockerConfig()

