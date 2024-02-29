#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""
配置分类：
1. Django使用的配置文件，写到settings中
2. 程序需要, 用户不需要更改的写到settings中
3. 程序需要, 用户需要更改的写到本config中
"""
import base64
import copy
import errno
import json
import logging
import os
import re
import sys
import types
from importlib import import_module
from urllib.parse import urljoin, urlparse, quote

import yaml
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BASE_DIR)
XPACK_DIR = os.path.join(BASE_DIR, 'xpack')
HAS_XPACK = os.path.isdir(XPACK_DIR)

logger = logging.getLogger('jumpserver.conf')


def import_string(dotted_path):
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError(
            'Module "%s" does not define a "%s" attribute/class' %
            (module_path, class_name)) from err


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


class ConfigCrypto:
    secret_keys = [
        'SECRET_KEY', 'DB_PASSWORD', 'REDIS_PASSWORD',
    ]

    def __init__(self, key):
        self.safe_key = self.process_key(key)
        self.sm4_encryptor = CryptSM4()
        self.sm4_encryptor.set_key(self.safe_key, SM4_ENCRYPT)

        self.sm4_decryptor = CryptSM4()
        self.sm4_decryptor.set_key(self.safe_key, SM4_DECRYPT)

    @staticmethod
    def process_key(secret_encrypt_key):
        key = secret_encrypt_key.encode()
        if len(key) >= 16:
            key = key[:16]
        else:
            key += b'\0' * (16 - len(key))
        return key

    def encrypt(self, data):
        data = bytes(data, encoding='utf8')
        return base64.b64encode(self.sm4_encryptor.crypt_ecb(data)).decode('utf8')

    def decrypt(self, data):
        data = base64.urlsafe_b64decode(bytes(data, encoding='utf8'))
        return self.sm4_decryptor.crypt_ecb(data).decode('utf8')

    def decrypt_if_need(self, value, item):
        if item not in self.secret_keys:
            return value

        try:
            plaintext = self.decrypt(value)
            if plaintext:
                value = plaintext
        except Exception as e:
            pass
        return value

    @classmethod
    def get_secret_encryptor(cls):
        # 使用 SM4 加密配置文件敏感信息
        # https://the-x.cn/cryptography/Sm4.aspx
        secret_encrypt_key = os.environ.get('SECRET_ENCRYPT_KEY', '')
        if not secret_encrypt_key:
            return None
        print('Info: try using SM4 to decrypt config secret value')
        return cls(secret_encrypt_key)


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
        'DEBUG_DEV': False,
        'DEBUG_ANSIBLE': False,
        'LOG_LEVEL': 'DEBUG',
        'LOG_DIR': os.path.join(PROJECT_DIR, 'data', 'logs'),
        'DB_ENGINE': 'mysql',
        'DB_NAME': 'jumpserver',
        'DB_HOST': '127.0.0.1',
        'DB_PORT': 3306,
        'DB_USER': 'root',
        'DB_PASSWORD': '',
        'DB_USE_SSL': False,
        'REDIS_HOST': '127.0.0.1',
        'REDIS_PORT': 6379,
        'REDIS_PASSWORD': '',
        'REDIS_USE_SSL': False,
        'REDIS_SSL_KEY': None,
        'REDIS_SSL_CERT': None,
        'REDIS_SSL_CA': None,
        'REDIS_SSL_REQUIRED': 'none',
        # Redis Sentinel
        'REDIS_SENTINEL_HOSTS': '',
        'REDIS_SENTINEL_PASSWORD': '',
        'REDIS_SENTINEL_SOCKET_TIMEOUT': None,
        # Default value
        'REDIS_DB_CELERY': 3,
        'REDIS_DB_CACHE': 4,
        'REDIS_DB_SESSION': 5,
        'REDIS_DB_WS': 6,

        'GLOBAL_ORG_DISPLAY_NAME': '',
        'SITE_URL': 'http://127.0.0.1',
        'USER_GUIDE_URL': '',
        'ANNOUNCEMENT_ENABLED': True,
        'ANNOUNCEMENT': {},

        # Security
        'X_FRAME_OPTIONS': 'DENY',

        # 未使用的配置
        'CAPTCHA_TEST_MODE': None,
        'DISPLAY_PER_PAGE': 25,

        'TOKEN_EXPIRATION': 3600 * 24,
        'DEFAULT_EXPIRED_YEARS': 70,
        'SESSION_COOKIE_DOMAIN': None,
        'CSRF_COOKIE_DOMAIN': None,
        'SESSION_COOKIE_NAME_PREFIX': None,
        'SESSION_COOKIE_AGE': 3600 * 24,
        'SESSION_EXPIRE_AT_BROWSER_CLOSE': False,
        'LOGIN_URL': reverse_lazy('authentication:login'),

        'CONNECTION_TOKEN_ONETIME_EXPIRATION': 5 * 60,  # 默认(new)
        'CONNECTION_TOKEN_EXPIRATION': 5 * 60,  # 默认(old)

        'CONNECTION_TOKEN_REUSABLE_EXPIRATION': 60 * 60 * 24 * 30,  # 最大(new)
        'CONNECTION_TOKEN_EXPIRATION_MAX': 60 * 60 * 24 * 30,  # 最大(old)
        'CONNECTION_TOKEN_REUSABLE': False,

        # Custom Config
        'AUTH_CUSTOM': False,
        'AUTH_CUSTOM_FILE_MD5': '',

        'MFA_CUSTOM': False,
        'MFA_CUSTOM_FILE_MD5': '',

        'SMS_CUSTOM_FILE_MD5': '',

        # 临时密码
        'AUTH_TEMP_TOKEN': False,

        # Vault
        'VAULT_ENABLED': False,
        'VAULT_HCP_HOST': '',
        'VAULT_HCP_TOKEN': '',
        'VAULT_HCP_MOUNT_POINT': 'jumpserver',

        'HISTORY_ACCOUNT_CLEAN_LIMIT': 999,

        # Cache login password
        'CACHE_LOGIN_PASSWORD_ENABLED': False,
        'CACHE_LOGIN_PASSWORD_TTL': 60 * 60 * 24,

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
        'AUTH_LDAP_SYNC_ORG_IDS': ['00000000-0000-0000-0000-000000000002'],
        'AUTH_LDAP_SYNC_RECEIVERS': [],
        'AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS': False,
        'AUTH_LDAP_OPTIONS_OPT_REFERRALS': -1,

        # OpenID 配置参数
        # OpenID 公有配置参数 (version <= 1.5.8 或 version >= 1.5.8)
        'AUTH_OPENID': False,
        'BASE_SITE_URL': None,
        'AUTH_OPENID_CLIENT_ID': 'client-id',
        'AUTH_OPENID_CLIENT_SECRET': 'client-secret',
        # https://openid.net/specs/openid-connect-core-1_0.html#ClientAuthentication
        'AUTH_OPENID_CLIENT_AUTH_METHOD': 'client_secret_basic',
        'AUTH_OPENID_SHARE_SESSION': True,
        'AUTH_OPENID_IGNORE_SSL_VERIFICATION': True,
        'AUTH_OPENID_USER_ATTR_MAP': {
            'name': 'name', 'username': 'preferred_username', 'email': 'email'
        },
        'AUTH_OPENID_PKCE': False,
        'AUTH_OPENID_CODE_CHALLENGE_METHOD': 'S256',

        # OpenID 新配置参数 (version >= 1.5.9)
        'AUTH_OPENID_PROVIDER_ENDPOINT': 'https://oidc.example.com/',
        'AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT': 'https://oidc.example.com/authorize',
        'AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT': 'https://oidc.example.com/token',
        'AUTH_OPENID_PROVIDER_JWKS_ENDPOINT': 'https://oidc.example.com/jwks',
        'AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT': 'https://oidc.example.com/userinfo',
        'AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT': 'https://oidc.example.com/logout',
        'AUTH_OPENID_PROVIDER_SIGNATURE_ALG': 'HS256',
        'AUTH_OPENID_PROVIDER_SIGNATURE_KEY': None,
        'AUTH_OPENID_SCOPES': 'openid profile email',
        'AUTH_OPENID_ID_TOKEN_MAX_AGE': 60,
        'AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS': True,
        'AUTH_OPENID_USE_STATE': True,
        'AUTH_OPENID_USE_NONCE': True,
        'AUTH_OPENID_ALWAYS_UPDATE_USER': True,

        # Keycloak 旧配置参数 (version <= 1.5.8 (discarded))
        'AUTH_OPENID_KEYCLOAK': True,
        'AUTH_OPENID_SERVER_URL': 'https://keycloak.example.com',
        'AUTH_OPENID_REALM_NAME': None,

        # Raidus 认证
        'AUTH_RADIUS': False,
        'RADIUS_SERVER': 'localhost',
        'RADIUS_PORT': 1812,
        'RADIUS_SECRET': '',
        'RADIUS_ATTRIBUTES': {},
        'RADIUS_ENCRYPT_PASSWORD': True,
        'OTP_IN_RADIUS': False,

        # Cas 认证
        'AUTH_CAS': False,
        'CAS_SERVER_URL': "https://example.com/cas/",
        'CAS_ROOT_PROXIED_AS': 'https://example.com',
        'CAS_LOGOUT_COMPLETELY': True,
        'CAS_VERSION': 3,
        'CAS_USERNAME_ATTRIBUTE': 'cas:user',
        'CAS_APPLY_ATTRIBUTES_TO_USER': False,
        'CAS_RENAME_ATTRIBUTES': {'cas:user': 'username'},
        'CAS_CREATE_USER': True,

        'AUTH_SSO': False,
        'AUTH_SSO_AUTHKEY_TTL': 60 * 15,

        # SAML2 认证
        'AUTH_SAML2': False,
        'SAML2_LOGOUT_COMPLETELY': True,
        'AUTH_SAML2_ALWAYS_UPDATE_USER': True,
        'SAML2_RENAME_ATTRIBUTES': {'uid': 'username', 'email': 'email'},
        'SAML2_SP_ADVANCED_SETTINGS': {
            "organization": {
                "en": {
                    "name": "JumpServer",
                    "displayname": "JumpServer",
                    "url": "https://jumpserver.org/"
                }
            },
            "strict": True,
            "security": {
            }
        },
        'SAML2_IDP_METADATA_URL': '',
        'SAML2_IDP_METADATA_XML': '',
        'SAML2_SP_KEY_CONTENT': '',
        'SAML2_SP_CERT_CONTENT': '',
        'AUTH_SAML2_PROVIDER_AUTHORIZATION_ENDPOINT': '/',
        'AUTH_SAML2_AUTHENTICATION_FAILURE_REDIRECT_URI': '/',

        # OAuth2 认证
        'AUTH_OAUTH2': False,
        'AUTH_OAUTH2_LOGO_PATH': 'img/login_oauth2_logo.png',
        'AUTH_OAUTH2_PROVIDER': 'OAuth2',
        'AUTH_OAUTH2_ALWAYS_UPDATE_USER': True,
        'AUTH_OAUTH2_CLIENT_ID': 'client-id',
        'AUTH_OAUTH2_SCOPE': '',
        'AUTH_OAUTH2_CLIENT_SECRET': '',
        'AUTH_OAUTH2_LOGOUT_COMPLETELY': True,
        'AUTH_OAUTH2_PROVIDER_AUTHORIZATION_ENDPOINT': 'https://oauth2.example.com/authorize',
        'AUTH_OAUTH2_PROVIDER_USERINFO_ENDPOINT': 'https://oauth2.example.com/userinfo',
        'AUTH_OAUTH2_PROVIDER_END_SESSION_ENDPOINT': 'https://oauth2.example.com/logout',
        'AUTH_OAUTH2_ACCESS_TOKEN_ENDPOINT': 'https://oauth2.example.com/access_token',
        'AUTH_OAUTH2_ACCESS_TOKEN_METHOD': 'GET',
        'AUTH_OAUTH2_USER_ATTR_MAP': {
            'name': 'name', 'username': 'username', 'email': 'email'
        },
        'AUTH_PASSKEY': False,
        'FIDO_SERVER_ID': '',
        'FIDO_SERVER_NAME': 'JumpServer',

        # 企业微信
        'AUTH_WECOM': False,
        'WECOM_CORPID': '',
        'WECOM_AGENTID': '',
        'WECOM_SECRET': '',

        # 钉钉
        'AUTH_DINGTALK': False,
        'DINGTALK_AGENTID': '',
        'DINGTALK_APPKEY': '',
        'DINGTALK_APPSECRET': '',

        # 飞书
        'AUTH_FEISHU': False,
        'FEISHU_APP_ID': '',
        'FEISHU_APP_SECRET': '',
        'FEISHU_VERSION': 'feishu',

        # Slack
        'AUTH_SLACK': False,
        'SLACK_CLIENT_ID': '',
        'SLACK_CLIENT_SECRET': '',
        'SLACK_BOT_TOKEN': '',

        'LOGIN_REDIRECT_TO_BACKEND': '',  # 'OPENID / CAS / SAML2
        'LOGIN_REDIRECT_MSG_ENABLED': True,

        'SMS_ENABLED': False,
        'SMS_BACKEND': '',
        'SMS_CODE_LENGTH': 4,
        'SMS_TEST_PHONE': '',

        'ALIBABA_ACCESS_KEY_ID': '',
        'ALIBABA_ACCESS_KEY_SECRET': '',
        'ALIBABA_VERIFY_SIGN_NAME': '',
        'ALIBABA_VERIFY_TEMPLATE_CODE': '',

        'TENCENT_SECRET_ID': '',
        'TENCENT_SECRET_KEY': '',
        'TENCENT_SDKAPPID': '',
        'TENCENT_VERIFY_SIGN_NAME': '',
        'TENCENT_VERIFY_TEMPLATE_CODE': '',

        'HUAWEI_APP_KEY': '',
        'HUAWEI_APP_SECRET': '',
        'HUAWEI_SMS_ENDPOINT': '',
        'HUAWEI_SIGN_CHANNEL_NUM': '',
        'HUAWEI_VERIFY_SIGN_NAME': '',
        'HUAWEI_VERIFY_TEMPLATE_CODE': '',

        'CMPP2_HOST': '',
        'CMPP2_PORT': 7890,
        'CMPP2_SP_ID': '',
        'CMPP2_SP_SECRET': '',
        'CMPP2_SRC_ID': '',
        'CMPP2_SERVICE_ID': '',
        'CMPP2_VERIFY_SIGN_NAME': '',
        'CMPP2_VERIFY_TEMPLATE_CODE': '{code}',

        'CUSTOM_SMS_URL': '',
        'CUSTOM_SMS_API_PARAMS': {'phone_numbers': '{phone_numbers}', 'content': _('The verification code is: {code}')},
        'CUSTOM_SMS_REQUEST_METHOD': 'get',

        # Email
        'EMAIL_PROTOCOL': 'smtp',
        'EMAIL_CUSTOM_USER_CREATED_SUBJECT': _('Create account successfully'),
        'EMAIL_CUSTOM_USER_CREATED_HONORIFIC': _('Hello'),
        'EMAIL_CUSTOM_USER_CREATED_BODY': _('Your account has been created successfully'),

        'OTP_VALID_WINDOW': 2,
        'OTP_ISSUER_NAME': 'JumpServer',
        'EMAIL_SUFFIX': 'example.com',

        # Terminal配置
        'TERMINAL_PASSWORD_AUTH': True,
        'TERMINAL_PUBLIC_KEY_AUTH': True,
        'TERMINAL_HEARTBEAT_INTERVAL': 20,
        'TERMINAL_ASSET_LIST_SORT_BY': 'name',
        'TERMINAL_ASSET_LIST_PAGE_SIZE': 'auto',
        'TERMINAL_SESSION_KEEP_DURATION': 200,
        'TERMINAL_HOST_KEY': '',
        'TERMINAL_COMMAND_STORAGE': {},
        # 未来废弃(目前迁移会用)
        'TERMINAL_RDP_ADDR': '',
        # 保留(Luna还在用)
        'TERMINAL_MAGNUS_ENABLED': True,
        'TERMINAL_KOKO_SSH_ENABLED': True,
        'TERMINAL_RAZOR_ENABLED': True,
        'TERMINAL_OMNIDB_ENABLED': True,

        # 安全配置
        'SECURITY_MFA_AUTH': 0,  # 0 不开启 1 全局开启 2 管理员开启
        'SECURITY_MFA_AUTH_ENABLED_FOR_THIRD_PARTY': True,
        'SECURITY_COMMAND_EXECUTION': True,
        'SECURITY_COMMAND_BLACKLIST': [
            'reboot', 'shutdown', 'poweroff', 'halt', 'dd', 'half', 'top'
        ],
        'SECURITY_SERVICE_ACCOUNT_REGISTRATION': True,
        'SECURITY_VIEW_AUTH_NEED_MFA': True,
        'SECURITY_MAX_IDLE_TIME': 30,
        'SECURITY_MAX_SESSION_TIME': 24,
        'SECURITY_PASSWORD_EXPIRATION_TIME': 9999,
        'SECURITY_PASSWORD_MIN_LENGTH': 6,
        'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH': 6,
        'SECURITY_PASSWORD_UPPER_CASE': False,
        'SECURITY_PASSWORD_LOWER_CASE': False,
        'SECURITY_PASSWORD_NUMBER': False,
        'SECURITY_PASSWORD_SPECIAL_CHAR': False,
        'SECURITY_MFA_IN_LOGIN_PAGE': False,
        'SECURITY_LOGIN_CHALLENGE_ENABLED': False,
        'SECURITY_LOGIN_CAPTCHA_ENABLED': True,
        'SECURITY_INSECURE_COMMAND': False,
        'SECURITY_INSECURE_COMMAND_LEVEL': 5,
        'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER': '',
        'SECURITY_LUNA_REMEMBER_AUTH': True,
        'SECURITY_WATERMARK_ENABLED': True,
        'SECURITY_MFA_VERIFY_TTL': 3600,
        'SECURITY_UNCOMMON_USERS_TTL': 999,
        'VERIFY_CODE_TTL': 60,
        'SECURITY_SESSION_SHARE': True,
        'SECURITY_CHECK_DIFFERENT_CITY_LOGIN': True,
        'OLD_PASSWORD_HISTORY_LIMIT_COUNT': 5,
        'CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED': True,
        'USER_LOGIN_SINGLE_MACHINE_ENABLED': False,
        'ONLY_ALLOW_EXIST_USER_AUTH': False,
        'ONLY_ALLOW_AUTH_FROM_SOURCE': False,
        # 用户登录限制的规则
        'SECURITY_LOGIN_LIMIT_COUNT': 7,
        'SECURITY_LOGIN_LIMIT_TIME': 30,
        # 登录IP限制的规则
        'SECURITY_LOGIN_IP_BLACK_LIST': [],
        'SECURITY_LOGIN_IP_WHITE_LIST': [],
        'SECURITY_LOGIN_IP_LIMIT_COUNT': 99999,
        'SECURITY_LOGIN_IP_LIMIT_TIME': 30,

        # 启动前
        'HTTP_BIND_HOST': '0.0.0.0',
        'HTTP_LISTEN_PORT': 8080,
        'WS_LISTEN_PORT': 8070,

        'SYSLOG_ADDR': '',  # '192.168.0.1:514'
        'SYSLOG_FACILITY': 'user',
        'SYSLOG_SOCKTYPE': 2,

        'PERM_EXPIRED_CHECK_PERIODIC': 60 * 60,
        'PERM_TREE_REGEN_INTERVAL': 1,
        'FLOWER_URL': "127.0.0.1:5555",
        'LANGUAGE_CODE': 'zh',
        'TIME_ZONE': 'Asia/Shanghai',
        'FORCE_SCRIPT_NAME': '',
        'SESSION_COOKIE_SECURE': False,
        'DOMAINS': '',
        'CSRF_COOKIE_SECURE': False,
        'REFERER_CHECK_ENABLED': False,
        'SESSION_ENGINE': 'cache',
        'SESSION_SAVE_EVERY_REQUEST': True,
        'SERVER_REPLAY_STORAGE': {},
        'SECURITY_DATA_CRYPTO_ALGO': None,
        'GMSSL_ENABLED': False,
        # 操作日志变更字段的存储ES配置
        'OPERATE_LOG_ELASTICSEARCH_CONFIG': {},
        # Magnus 组件需要监听的 Oracle 端口范围
        'MAGNUS_ORACLE_PORTS': '30000-30030',

        # 记录清理清理
        'LOGIN_LOG_KEEP_DAYS': 180,
        'TASK_LOG_KEEP_DAYS': 180,
        'OPERATE_LOG_KEEP_DAYS': 180,
        'ACTIVITY_LOG_KEEP_DAYS': 180,
        'FTP_LOG_KEEP_DAYS': 180,
        'CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS': 180,
        'JOB_EXECUTION_KEEP_DAYS': 180,
        'PASSWORD_CHANGE_LOG_KEEP_DAYS': 999,

        'TICKETS_ENABLED': True,
        'TICKETS_DIRECT_APPROVE': False,

        # 废弃的
        'DEFAULT_ORG_SHOW_ALL_USERS': True,
        'ORG_CHANGE_TO_URL': '',
        'WINDOWS_SKIP_ALL_MANUAL_PASSWORD': False,
        'CONNECTION_TOKEN_ENABLED': False,

        'PERM_SINGLE_ASSET_TO_UNGROUP_NODE': False,
        'TICKET_AUTHORIZE_DEFAULT_TIME': 7,
        'TICKET_AUTHORIZE_DEFAULT_TIME_UNIT': 'day',
        'PERIOD_TASK_ENABLED': True,
        'TERMINAL_TELNET_REGEX': '',

        # 导航栏 帮助
        'HELP_DOCUMENT_URL': 'https://docs.jumpserver.org/zh/v3/',
        'HELP_SUPPORT_URL': 'http://www.jumpserver.org/support/',

        'FORGOT_PASSWORD_URL': '',
        'HEALTH_CHECK_TOKEN': '',

        # Applet 等软件的下载地址
        'APPLET_DOWNLOAD_HOST': '',

        # FTP 文件上传下载备份阈值，单位(M)，当值小于等于0时，不备份
        'FTP_FILE_MAX_STORE': 0,

        # API 分页
        'MAX_LIMIT_PER_PAGE': 10000,
        'DEFAULT_PAGE_SIZE': None,

        'LIMIT_SUPER_PRIV': False,

        # Chat AI
        'CHAT_AI_ENABLED': False,
        'GPT_API_KEY': '',
        'GPT_BASE_URL': '',
        'GPT_PROXY': '',
        'GPT_MODEL': 'gpt-3.5-turbo',
        'VIRTUAL_APP_ENABLED': False,

        'FILE_UPLOAD_SIZE_LIMIT_MB': 200,

        'TICKET_APPLY_ASSET_SCOPE': 'all'
    }

    old_config_map = {
        'CONNECTION_TOKEN_ONETIME_EXPIRATION': 'CONNECTION_TOKEN_EXPIRATION',
        'CONNECTION_TOKEN_REUSABLE_EXPIRATION': 'CONNECTION_TOKEN_EXPIRATION_MAX',
    }

    def __init__(self, *args):
        super().__init__(*args)
        self.secret_encryptor = ConfigCrypto.get_secret_encryptor()

    @staticmethod
    def convert_keycloak_to_openid(keycloak_config):
        """
        兼容OpenID旧配置 (即 version <= 1.5.8)
        因为旧配置只支持OpenID协议的Keycloak实现,
        所以只需要根据旧配置和Keycloak的Endpoint说明文档，
        构造出新配置中标准OpenID协议中所需的Endpoint即可
        (Keycloak说明文档参考: https://www.keycloak.org/docs/latest/securing_apps/)
        """

        openid_config = copy.deepcopy(keycloak_config)
        auth_openid = openid_config.get('AUTH_OPENID')
        auth_openid_realm_name = openid_config.get('AUTH_OPENID_REALM_NAME')
        auth_openid_server_url = openid_config.get('AUTH_OPENID_SERVER_URL')

        if not auth_openid:
            return

        if auth_openid and not auth_openid_realm_name:
            # 开启的是标准 OpenID 配置，关掉 Keycloak 配置
            openid_config.update({
                'AUTH_OPENID_KEYCLOAK': False
            })

        if auth_openid_realm_name is None:
            return

        # # convert key # #
        compatible_config = {
            'AUTH_OPENID_PROVIDER_ENDPOINT': auth_openid_server_url,

            'AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT': '/realms/{}/protocol/openid-connect/auth'
                                                           ''.format(auth_openid_realm_name),
            'AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT': '/realms/{}/protocol/openid-connect/token'
                                                   ''.format(auth_openid_realm_name),
            'AUTH_OPENID_PROVIDER_JWKS_ENDPOINT': '/realms/{}/protocol/openid-connect/certs'
                                                  ''.format(auth_openid_realm_name),
            'AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT': '/realms/{}/protocol/openid-connect/userinfo'
                                                      ''.format(auth_openid_realm_name),
            'AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT': '/realms/{}/protocol/openid-connect/logout'
                                                         ''.format(auth_openid_realm_name)
        }
        for key, value in compatible_config.items():
            openid_config[key] = value

        # # convert value # #
        """ 兼容值的绝对路径、相对路径 (key 为 AUTH_OPENID_PROVIDER_*_ENDPOINT 的配置) """
        base = openid_config.get('AUTH_OPENID_PROVIDER_ENDPOINT')
        for key, value in openid_config.items():
            result = re.match(r'^AUTH_OPENID_PROVIDER_.*_ENDPOINT$', key)
            if result is None:
                continue
            if value is None:
                # None 在 url 中有特殊含义 (比如对于: end_session_endpoint)
                continue

            value = build_absolute_uri(base, value)
            openid_config[key] = value

        return openid_config

    def get_keycloak_config(self):
        keycloak_config = {
            'AUTH_OPENID': self.AUTH_OPENID,
            'AUTH_OPENID_REALM_NAME': self.AUTH_OPENID_REALM_NAME,
            'AUTH_OPENID_SERVER_URL': self.AUTH_OPENID_SERVER_URL,
            'AUTH_OPENID_PROVIDER_ENDPOINT': self.AUTH_OPENID_PROVIDER_ENDPOINT
        }
        return keycloak_config

    def set_openid_config(self, openid_config):
        for key, value in openid_config.items():
            self[key] = value

    def compatible_auth_openid(self, keycloak_config=None):
        if keycloak_config is None:
            keycloak_config = self.get_keycloak_config()
        openid_config = self.convert_keycloak_to_openid(keycloak_config)
        if openid_config:
            self.set_openid_config(openid_config)

    def compatible_redis(self):
        redis_config = {
            'REDIS_PASSWORD': str(self.REDIS_PASSWORD),
            'REDIS_PASSWORD_QUOTE': quote(str(self.REDIS_PASSWORD)),
        }
        for key, value in redis_config.items():
            self[key] = value

    def compatible(self):
        """
        对配置做兼容处理
        1. 对`key`的兼容 (例如：版本升级)
        2. 对`value`做兼容 (例如：True、true、1 => True)

        处理顺序要保持先对key做处理, 再对value做处理,
        因为处理value的时候，只根据最新版本支持的key进行
        """
        # 兼容 OpenID 配置
        self.compatible_auth_openid()
        # 兼容 Redis 配置
        self.compatible_redis()

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

    def get(self, item, default=None):
        # 再从配置文件中获取
        value = self.get_from_config(item)
        if value is None:
            value = self.get_from_env(item)

        # 因为要递归，所以优先从上次返回的递归中获取
        if default is None:
            default = self.defaults.get(item)
        if value is None and item in self.old_config_map:
            return self.get(self.old_config_map[item], default)
        if value is None:
            value = default
        if self.secret_encryptor:
            value = self.secret_encryptor.decrypt_if_need(value, item)
        return value

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
        except ImportError:
            return False
        if c:
            self.from_object(c)
            return True
        else:
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
