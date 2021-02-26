#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""
配置分类：
1. Django使用的配置文件，写到settings中
2. 程序需要, 用户不需要更改的写到settings中
3. 程序需要, 用户需要更改的写到本config中
"""
import os
import re
import sys
import types
import errno
import json
import yaml
from importlib import import_module
from django.urls import reverse_lazy
from django.templatetags.static import static
from urllib.parse import urljoin, urlparse
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
XPACK_DIR = os.path.join(BASE_DIR, 'xpack')
HAS_XPACK = os.path.isdir(XPACK_DIR)


def import_string(dotted_path):
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (
            module_path, class_name)
        ) from err


def is_absolute_uri(uri):
    """ 判断一个uri是否是绝对地址 """
    if not isinstance(uri, str):
        return False

    result = re.match(r'^http[s]?://.*', uri)
    if result is None:
        return False

    return True


def build_absolute_uri(base, uri):
    """ 构建绝对uri地址 """
    if uri is None:
        return base

    if isinstance(uri, int):
        uri = str(uri)

    if not isinstance(uri, str):
        return base

    if is_absolute_uri(uri):
        return uri

    parsed_base = urlparse(base)
    url = "{}://{}".format(parsed_base.scheme, parsed_base.netloc)
    path = '{}/{}/'.format(parsed_base.path.strip('/'), uri.strip('/'))
    return urljoin(url, path)


class DoesNotExist(Exception):
    pass


class Config(dict):
    """Works exactly like a dict but provides ways to fill it from files
    or special dictionaries.  There are two common patterns to populate the
    config.

    Either you can fill the config from a config file::

        app.config.from_pyfile('yourconfig.cfg')

    Or alternatively you can define the configuration options in the
    module that calls :meth:`from_object` or provide an import path to
    a module that should be loaded.  It is also possible to tell it to
    use the same module and with that provide the configuration values
    just before the call::

        DEBUG = True
        SECRET_KEY = 'development key'
        app.config.from_object(__name__)

    In both cases (loading from any Python file or loading from modules),
    only uppercase keys are added to the config.  This makes it possible to use
    lowercase values in the config file for temporary values that are not added
    to the config or to define the config keys in the same file that implements
    the application.

    Probably the most interesting way to load configurations is from an
    environment variable pointing to a file::

        app.config.from_envvar('YOURAPPLICATION_SETTINGS')

    In this case before launching the application you have to set this
    environment variable to the file you want to use.  On Linux and OS X
    use the export statement::

        export YOURAPPLICATION_SETTINGS='/path/to/config/file'

    On windows use `set` instead.

    :param root_path: path to which files are read relative from.  When the
                      config object is created by the application, this is
                      the application's :attr:`~flask.Flask.root_path`.
    :param defaults: an optional dictionary of default values
    """
    defaults = {
        # Django Config, Must set before start
        'SECRET_KEY': '',
        'BOOTSTRAP_TOKEN': '',
        'DEBUG': False,
        'LOG_LEVEL': 'DEBUG',
        'LOG_DIR': os.path.join(PROJECT_DIR, 'logs'),
        'DB_ENGINE': 'mysql',
        'DB_NAME': 'jumpserver',
        'DB_HOST': '127.0.0.1',
        'DB_PORT': 3306,
        'DB_USER': 'root',
        'DB_PASSWORD': '',
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'REDIS_PASSWORD': '',
        # Default value
        'REDIS_DB_CELERY': 3,
        'REDIS_DB_CACHE': 4,
        'REDIS_DB_SESSION': 5,
        'REDIS_DB_WS': 6,

        'SITE_URL': 'http://localhost:8080',
        'CAPTCHA_TEST_MODE': None,
        'TOKEN_EXPIRATION': 3600 * 24,
        'DISPLAY_PER_PAGE': 25,
        'DEFAULT_EXPIRED_YEARS': 70,
        'SESSION_COOKIE_DOMAIN': None,
        'CSRF_COOKIE_DOMAIN': None,
        'SESSION_COOKIE_AGE': 3600 * 24,
        'SESSION_EXPIRE_AT_BROWSER_CLOSE': False,
        'LOGIN_URL': reverse_lazy('authentication:login'),

        # Custom Config
        # Auth LDAP settings
        'AUTH_LDAP': False,
        'AUTH_LDAP_SERVER_URI': 'ldap://localhost:389',
        'AUTH_LDAP_BIND_DN': 'cn=admin,dc=jumpserver,dc=org',
        'AUTH_LDAP_BIND_PASSWORD': '',
        'AUTH_LDAP_SEARCH_OU': 'ou=tech,dc=jumpserver,dc=org',
        'AUTH_LDAP_SEARCH_FILTER': '(cn=%(user)s)',
        'AUTH_LDAP_START_TLS': False,
        'AUTH_LDAP_USER_ATTR_MAP': {"username": "cn", "name": "sn", "email": "mail"},
        'AUTH_LDAP_CONNECT_TIMEOUT': 10,
        'AUTH_LDAP_SEARCH_PAGED_SIZE': 1000,
        'AUTH_LDAP_SYNC_IS_PERIODIC': False,
        'AUTH_LDAP_SYNC_INTERVAL': None,
        'AUTH_LDAP_SYNC_CRONTAB': None,
        'AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS': False,
        'AUTH_LDAP_OPTIONS_OPT_REFERRALS': -1,

        # OpenID 配置参数
        # OpenID 公有配置参数 (version <= 1.5.8 或 version >= 1.5.8)
        'AUTH_OPENID': False,
        'BASE_SITE_URL': None,
        'AUTH_OPENID_CLIENT_ID': 'client-id',
        'AUTH_OPENID_CLIENT_SECRET': 'client-secret',
        'AUTH_OPENID_SHARE_SESSION': True,
        'AUTH_OPENID_IGNORE_SSL_VERIFICATION': True,
        # OpenID 新配置参数 (version >= 1.5.9)
        'AUTH_OPENID_PROVIDER_ENDPOINT': 'https://op-example.com/',
        'AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT': 'https://op-example.com/authorize',
        'AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT': 'https://op-example.com/token',
        'AUTH_OPENID_PROVIDER_JWKS_ENDPOINT': 'https://op-example.com/jwks',
        'AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT': 'https://op-example.com/userinfo',
        'AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT': 'https://op-example.com/logout',
        'AUTH_OPENID_PROVIDER_SIGNATURE_ALG': 'HS256',
        'AUTH_OPENID_PROVIDER_SIGNATURE_KEY': None,
        'AUTH_OPENID_SCOPES': 'openid profile email',
        'AUTH_OPENID_ID_TOKEN_MAX_AGE': 60,
        'AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS': True,
        'AUTH_OPENID_USE_STATE': True,
        'AUTH_OPENID_USE_NONCE': True,
        'AUTH_OPENID_ALWAYS_UPDATE_USER': True,
        # OpenID 旧配置参数 (version <= 1.5.8 (discarded))
        'AUTH_OPENID_SERVER_URL': 'http://openid',
        'AUTH_OPENID_REALM_NAME': None,

        'AUTH_RADIUS': False,
        'RADIUS_SERVER': 'localhost',
        'RADIUS_PORT': 1812,
        'RADIUS_SECRET': '',
        'RADIUS_ENCRYPT_PASSWORD': True,
        'OTP_IN_RADIUS': False,

        'AUTH_CAS': False,
        'CAS_SERVER_URL': "http://host/cas/",
        'CAS_ROOT_PROXIED_AS': '',
        'CAS_LOGOUT_COMPLETELY': True,
        'CAS_VERSION': 3,

        'AUTH_SSO': False,
        'AUTH_SSO_AUTHKEY_TTL': 60 * 15,

        'OTP_VALID_WINDOW': 2,
        'OTP_ISSUER_NAME': 'JumpServer',
        'EMAIL_SUFFIX': 'jumpserver.org',

        'TERMINAL_PASSWORD_AUTH': True,
        'TERMINAL_PUBLIC_KEY_AUTH': True,
        'TERMINAL_HEARTBEAT_INTERVAL': 20,
        'TERMINAL_ASSET_LIST_SORT_BY': 'hostname',
        'TERMINAL_ASSET_LIST_PAGE_SIZE': 'auto',
        'TERMINAL_SESSION_KEEP_DURATION': 200,
        'TERMINAL_HOST_KEY': '',
        'TERMINAL_TELNET_REGEX': '',
        'TERMINAL_COMMAND_STORAGE': {},

        'SECURITY_MFA_AUTH': False,
        'SECURITY_COMMAND_EXECUTION': True,
        'SECURITY_SERVICE_ACCOUNT_REGISTRATION': True,
        'SECURITY_VIEW_AUTH_NEED_MFA': True,
        'SECURITY_LOGIN_LIMIT_COUNT': 7,
        'SECURITY_LOGIN_LIMIT_TIME': 30,
        'SECURITY_MAX_IDLE_TIME': 30,
        'SECURITY_PASSWORD_EXPIRATION_TIME': 9999,
        'SECURITY_PASSWORD_MIN_LENGTH': 6,
        'SECURITY_PASSWORD_UPPER_CASE': False,
        'SECURITY_PASSWORD_LOWER_CASE': False,
        'SECURITY_PASSWORD_NUMBER': False,
        'SECURITY_PASSWORD_SPECIAL_CHAR': False,
        'SECURITY_LOGIN_CHALLENGE_ENABLED': False,
        'SECURITY_LOGIN_CAPTCHA_ENABLED': True,
        'SECURITY_DATA_CRYPTO_ALGO': 'aes',
        'SECURITY_INSECURE_COMMAND': False,
        'SECURITY_INSECURE_COMMAND_LEVEL': 5,
        'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER': '',

        'HTTP_BIND_HOST': '0.0.0.0',
        'HTTP_LISTEN_PORT': 8080,
        'WS_LISTEN_PORT': 8070,
        'LOGIN_LOG_KEEP_DAYS': 200,
        'TASK_LOG_KEEP_DAYS': 90,
        'OPERATE_LOG_KEEP_DAYS': 200,
        'FTP_LOG_KEEP_DAYS': 200,
        'ASSETS_PERM_CACHE_TIME': 3600 * 24,
        'SECURITY_MFA_VERIFY_TTL': 3600,
        'ASSETS_PERM_CACHE_ENABLE': HAS_XPACK,
        'SYSLOG_ADDR': '',  # '192.168.0.1:514'
        'SYSLOG_FACILITY': 'user',
        'SYSLOG_SOCKTYPE': 2,
        'PERM_SINGLE_ASSET_TO_UNGROUP_NODE': False,
        'PERM_EXPIRED_CHECK_PERIODIC': 60 * 60,
        'WINDOWS_SSH_DEFAULT_SHELL': 'cmd',
        'FLOWER_URL': "127.0.0.1:5555",
        'DEFAULT_ORG_SHOW_ALL_USERS': True,
        'PERIOD_TASK_ENABLE': True,
        'FORCE_SCRIPT_NAME': '',
        'LOGIN_CONFIRM_ENABLE': False,
        'WINDOWS_SKIP_ALL_MANUAL_PASSWORD': False,
        'ORG_CHANGE_TO_URL': '',
        'LANGUAGE_CODE': 'zh',
        'TIME_ZONE': 'Asia/Shanghai',
        'CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED': True,
        'USER_LOGIN_SINGLE_MACHINE_ENABLED': False,
        'TICKETS_ENABLED': True,
        'SESSION_COOKIE_SECURE': False,
        'CSRF_COOKIE_SECURE': False,
        'REFERER_CHECK_ENABLED': False,
        'SERVER_REPLAY_STORAGE': {},
        'CONNECTION_TOKEN_ENABLED': False,
        'ONLY_ALLOW_EXIST_USER_AUTH': False,
        'ONLY_ALLOW_AUTH_FROM_SOURCE': True,
        'DISK_CHECK_ENABLED': True,
    }

    def compatible_auth_openid_of_key(self):
        """
        兼容OpenID旧配置 (即 version <= 1.5.8)
        因为旧配置只支持OpenID协议的Keycloak实现,
        所以只需要根据旧配置和Keycloak的Endpoint说明文档，
        构造出新配置中标准OpenID协议中所需的Endpoint即可
        (Keycloak说明文档参考: https://www.keycloak.org/docs/latest/securing_apps/)
        """
        if not self.AUTH_OPENID:
            return

        realm_name = self.AUTH_OPENID_REALM_NAME
        if realm_name is None:
            return

        compatible_keycloak_config = [
            (
                'AUTH_OPENID_PROVIDER_ENDPOINT',
                self.AUTH_OPENID_SERVER_URL
            ),
            (
                'AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT',
                '/realms/{}/protocol/openid-connect/auth'.format(realm_name)
            ),
            (
                'AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT',
                '/realms/{}/protocol/openid-connect/token'.format(realm_name)
            ),
            (
                'AUTH_OPENID_PROVIDER_JWKS_ENDPOINT',
                '/realms/{}/protocol/openid-connect/certs'.format(realm_name)
            ),
            (
                'AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT',
                '/realms/{}/protocol/openid-connect/userinfo'.format(realm_name)
            ),
            (
                'AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT',
                '/realms/{}/protocol/openid-connect/logout'.format(realm_name)
            )
        ]
        for key, value in compatible_keycloak_config:
            self[key] = value

    def compatible_auth_openid_of_value(self):
        """
        兼容值的绝对路径、相对路径
        (key 为 AUTH_OPENID_PROVIDER_*_ENDPOINT 的配置)
        """
        if not self.AUTH_OPENID:
            return

        base = self.AUTH_OPENID_PROVIDER_ENDPOINT
        config = list(self.items())
        for key, value in config:
            result = re.match(r'^AUTH_OPENID_PROVIDER_.*_ENDPOINT$', key)
            if result is None:
                continue
            if value is None:
                # None 在 url 中有特殊含义 (比如对于: end_session_endpoint)
                continue
            value = build_absolute_uri(base, value)
            self[key] = value

    def compatible(self):
        """
        对配置做兼容处理
        1. 对`key`的兼容 (例如：版本升级)
        2. 对`value`做兼容 (例如：True、true、1 => True)

        处理顺序要保持先对key做处理, 再对value做处理,
        因为处理value的时候，只根据最新版本支持的key进行
        """
        parts = ['key', 'value']
        targets = ['auth_openid']
        for part in parts:
            for target in targets:
                method_name = 'compatible_{}_of_{}'.format(target, part)
                method = getattr(self, method_name, None)
                if method is not None:
                    method()

    def convert_type(self, k, v):
        default_value = self.defaults.get(k)
        if default_value is None:
            return v
        tp = type(default_value)
        # 对bool特殊处理
        if tp is bool and isinstance(v, str):
            if v.lower() in ("true", "1"):
                return True
            else:
                return False
        if tp in [list, dict] and isinstance(v, str):
            try:
                v = json.loads(v)
                return v
            except json.JSONDecodeError:
                return v

        try:
            if tp in [list, dict]:
                v = json.loads(v)
            else:
                v = tp(v)
        except Exception:
            pass
        return v

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, dict.__repr__(self))

    def get_from_config(self, item):
        try:
            value = super().__getitem__(item)
        except KeyError:
            value = None
        return value

    def get_from_env(self, item):
        value = os.environ.get(item, None)
        if value is not None:
            value = self.convert_type(item, value)
        return value

    def get(self, item):
        # 再从配置文件中获取
        value = self.get_from_config(item)
        if value is not None:
            return value
        # 其次从环境变量来
        value = self.get_from_env(item)
        if value is not None:
            return value
        return self.defaults.get(item)

    def __getitem__(self, item):
        return self.get(item)

    def __getattr__(self, item):
        return self.get(item)


class ConfigManager:
    config_class = Config

    def __init__(self, root_path=None):
        self.root_path = root_path
        self.config = self.config_class()

    def from_pyfile(self, filename, silent=False):
        """Updates the values in the config from a Python file.  This function
        behaves as if the file was imported as module with the
        :meth:`from_object` function.

        :param filename: the filename of the config.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        :param silent: set to ``True`` if you want silent failure for missing
                       files.

        .. versionadded:: 0.7
           `silent` parameter.
        """
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        d = types.ModuleType('config')
        d.__file__ = filename
        try:
            with open(filename, mode='rb') as config_file:
                exec(compile(config_file.read(), filename, 'exec'), d.__dict__)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        self.from_object(d)
        return True

    def from_object(self, obj):
        """Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes. :meth:`from_object`
        loads only the uppercase attributes of the module/class. A ``dict``
        object will not work with :meth:`from_object` because the keys of a
        ``dict`` are not attributes of the ``dict`` class.

        Example of module-based configuration::

            app.config.from_object('yourapplication.default_config')
            from yourapplication import default_config
            app.config.from_object(default_config)

        You should not use this function to load the actual configuration but
        rather configuration defaults.  The actual config should be loaded
        with :meth:`from_pyfile` and ideally from a location not within the
        package because the package might be installed system wide.

        See :ref:`config-dev-prod` for an example of class-based configuration
        using :meth:`from_object`.

        :param obj: an import name or object
        """
        if isinstance(obj, str):
            obj = import_string(obj)
        for key in dir(obj):
            if key.isupper():
                self.config[key] = getattr(obj, key)

    def from_json(self, filename, silent=False):
        """Updates the values in the config from a JSON file. This function
        behaves as if the JSON object was a dictionary and passed to the
        :meth:`from_mapping` function.

        :param filename: the filename of the JSON file.  This can either be an
                         absolute filename or a filename relative to the
                         root path.
        :param silent: set to ``True`` if you want silent failure for missing
                       files.

        .. versionadded:: 0.11
        """
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        try:
            with open(filename) as json_file:
                obj = json.loads(json_file.read())
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        return self.from_mapping(obj)

    def from_yaml(self, filename, silent=False):
        if self.root_path:
            filename = os.path.join(self.root_path, filename)
        try:
            with open(filename, 'rt', encoding='utf8') as f:
                obj = yaml.safe_load(f)
        except IOError as e:
            if silent and e.errno in (errno.ENOENT, errno.EISDIR):
                return False
            e.strerror = 'Unable to load configuration file (%s)' % e.strerror
            raise
        if obj:
            return self.from_mapping(obj)
        return True

    def from_mapping(self, *mapping, **kwargs):
        """Updates the config like :meth:`update` ignoring items with non-upper
        keys.

        .. versionadded:: 0.11
        """
        mappings = []
        if len(mapping) == 1:
            if hasattr(mapping[0], 'items'):
                mappings.append(mapping[0].items())
            else:
                mappings.append(mapping[0])
        elif len(mapping) > 1:
            raise TypeError(
                'expected at most 1 positional argument, got %d' % len(mapping)
            )
        mappings.append(kwargs.items())
        for mapping in mappings:
            for (key, value) in mapping:
                if key.isupper():
                    self.config[key] = value
        return True

    def load_from_object(self):
        sys.path.insert(0, PROJECT_DIR)
        try:
            from config import config as c
            self.from_object(c)
            return True
        except ImportError:
            pass
        return False

    def load_from_yml(self):
        for i in ['config.yml', 'config.yaml']:
            if not os.path.isfile(os.path.join(self.root_path, i)):
                continue
            loaded = self.from_yaml(i)
            if loaded:
                return True
        return False

    @classmethod
    def load_user_config(cls, root_path=None, config_class=None):
        config_class = config_class or Config
        cls.config_class = config_class
        if not root_path:
            root_path = PROJECT_DIR

        manager = cls(root_path=root_path)
        if manager.load_from_object():
            config = manager.config
        elif manager.load_from_yml():
            config = manager.config
        else:
            msg = """

            Error: No config file found.

            You can run `cp config_example.yml config.yml`, and edit it.
            """
            raise ImportError(msg)

        # 对config进行兼容处理
        config.compatible()
        return config
