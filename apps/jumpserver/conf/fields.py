import os
from django.utils.translation import ugettext_lazy as _

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROJECT_DIR = os.path.dirname(BASE_DIR)
XPACK_DIR = os.path.join(BASE_DIR, 'xpack')
HAS_XPACK = os.path.isdir(XPACK_DIR)


FIELDS = {
    # Django 配置，需要通过配置文件完成，启动前设置，不支持更改
    'SECRET_KEY': {
        'type': 'str', 'label': _('SECRET_KEY'),
        'hidden': True, 'help_text': _("The key for encrypt every thing in system"),
        'required': True,
    },
    'DEBUG': {
        'type': 'bool', 'label': _('DEBUG'),
        'hidden': True, 'help_text': _("If debug, in development mode"),
        'default': False
    },
    'LOG_LEVEL': {
        'type': 'choice', 'label': _('LOG_LEVEL'), 'hidden': True,
        'choices': (
            ('DEBUG', 'DEBUG'),
            ('INFO', 'INFO'),
            ('ERROR', 'ERROR'),
        ),
        'default': 'INFO', 'help_text': _('The log level'),
    },
    'LOG_DIR': {
        'type': 'str', 'hidden': True,
        'label': 'LOG_DIR',
        'default': os.path.join(PROJECT_DIR, '../../../logs'),
    },
    'LANGUAGE_CODE': 'zh',
    'TIME_ZONE': 'Asia/Shanghai',
    'SESSION_COOKIE_SECURE': False,
    'SESSION_SAVE_EVERY_REQUEST': True,
    'CSRF_COOKIE_DOMAIN': None,
    'SESSION_COOKIE_DOMAIN': None,
    'BOOTSTRAP_TOKEN': {
        'type': 'str', 'label': _('BOOTSTRAP_TOKEN'),
        'hidden': True, 'help_text': '', 'required': True
    },
    'HTTP_BIND_HOST': '0.0.0.0',
    'HTTP_LISTEN_PORT': 8080,
    'WS_LISTEN_PORT': 8070,
    'FORCE_SCRIPT_NAME': '',
    'SECURITY_DATA_CRYPTO_ALGO': 'aes',

    # 数据库配置
    'DB_ENGINE': {
        'type': 'choice', 'label': 'DB_ENGINE',
        'choices': (
            ('mysql', 'MySQL'),
            ('postgre', 'PostgreSQL'),
            ('oracle', 'Oracle')
        ),
        'default': 'mysql',
        'hidden': True
    },
    'DB_NAME': {
        'type': 'str', 'label': "DB_NAME", 'hidden': True,
        'default': 'jumpserver', 'required': True
    },
    'DB_HOST': {
        'type': 'str', 'default': '127.0.0.1',
        'hidden': True, 'required': True
    },
    'DB_PORT': 3306,
    'DB_USER': 'root',
    'DB_PASSWORD': '',

    # Redis 配置
    'REDIS_HOST': '127.0.0.1',
    'REDIS_PORT': 6379,
    'REDIS_PASSWORD': '',
    'REDIS_DB_CACHE': 4,
    'REDIS_DB_CELERY': 3,
    'REDIS_DB_SESSION': 5,
    'REDIS_DB_WS': 6,

    # Generic Settings
    'SITE_URL': 'http://localhost:8080',
    'USER_GUIDE_URL': '',

    # SMTP Settings
    'EMAIL_HOST': {
        'type': 'str', 'label': _('SMTP host'),
        'required': True, 'max_length': 4096,
    },
    'EMAIL_PORT': {
        'type': 'int', 'label': _('SMTP port'),
        'required': True, 'max_length': 5
    },
    'EMAIL_HOST_USER': {
        'type': 'str', 'label': 'SMTP account',
        'required': True, 'max_length': 1024
    },
    'EMAIL_HOST_PASSWORD': {
        'type': 'str', 'label': 'SMTP password',
        'write_only': True, 'required': False,
        'help_text': _("Tips: Some provider use token except password")
    },
    'EMAIL_FROM': {
        'type': 'str', 'label': _('Send user'),
        'required': False, 'max_length': 1024,
        'help_text': _('Tips: Send mail account, default SMTP account as the send account')
    },
    'EMAIL_RECIPIENT': {
        'type': 'str', 'label': _('Test recipient'),
        'help_text': _('Tips: Used only as a test mail recipient')
    },
    'EMAIL_USE_SSL': {
        'type': 'bool', 'label': _('Use SSL'), 'required': False,
        'help_text': _('If SMTP port is 465, may be select')
    },
    'EMAIL_USE_TLS': {
        'type': 'bool', 'label': _('Use TLS'), 'required': False,
        'help_text': _('If SMTP port is 587, may be select')
    },
    'EMAIL_SUBJECT_PREFIX': {
        'type': 'str', 'label': _('Subject prefix'),
        'required': True, 'max_length': 1024
    },

    # Custom Config
    # Auth LDAP Settings
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

    # Radius 认证
    'AUTH_RADIUS': False,
    'RADIUS_SERVER': 'localhost',
    'RADIUS_PORT': 1812,
    'RADIUS_SECRET': '',
    'RADIUS_ENCRYPT_PASSWORD': True,
    'OTP_IN_RADIUS': False,

    # CAS 认证
    'AUTH_CAS': False,
    'CAS_SERVER_URL': "http://host/cas/",
    'CAS_ROOT_PROXIED_AS': '',
    'CAS_LOGOUT_COMPLETELY': True,
    'CAS_VERSION': 3,

    # Terminal 相关配置
    'TERMINAL_PASSWORD_AUTH': True,
    'TERMINAL_PUBLIC_KEY_AUTH': True,
    'TERMINAL_ASSET_LIST_SORT_BY': 'hostname',
    'TERMINAL_ASSET_LIST_PAGE_SIZE': 'auto',
    'TERMINAL_SESSION_KEEP_DURATION': 200,
    'TERMINAL_HOST_KEY': '',
    'TERMINAL_TELNET_REGEX': '',
    'TERMINAL_COMMAND_STORAGE': {},
    'WINDOWS_SKIP_ALL_MANUAL_PASSWORD': False,
    'SERVER_REPLAY_STORAGE': {},

    # 安全相关配置
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
    'SECURITY_INSECURE_COMMAND': False,
    'SECURITY_INSECURE_COMMAND_LEVEL': 5,
    'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER': '',
    'SECURITY_MFA_VERIFY_TTL': 3600,
    'REFERER_CHECK_ENABLED': False,

    # 登录安全相关
    'CONNECTION_TOKEN_ENABLED': False,
    'ONLY_ALLOW_EXIST_USER_AUTH': False,
    'ONLY_ALLOW_AUTH_FROM_SOURCE': False,
    'SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE': False,
    'USER_LOGIN_SINGLE_MACHINE_ENABLED': False,
    'FORGOT_PASSWORD_URL': '',
    'SESSION_COOKIE_AGE': 3600 * 24,
    'TOKEN_EXPIRATION': 3600 * 24,
    'OTP_VALID_WINDOW': 2,
    'OTP_ISSUER_NAME': 'JumpServer',
    # SSO 认证
    'AUTH_SSO': False,
    'AUTH_SSO_AUTHKEY_TTL': 60 * 15,

    # 日志保存相关配置
    'LOGIN_LOG_KEEP_DAYS': 200,
    'TASK_LOG_KEEP_DAYS': 90,
    'OPERATE_LOG_KEEP_DAYS': 200,
    'FTP_LOG_KEEP_DAYS': 200,
    'SYSLOG_ENABLE': False,
    'SYSLOG_ADDR': '',  # '192.168.0.1:514'
    'SYSLOG_FACILITY': 'user',
    'SYSLOG_SOCKTYPE': 2,

    # 授权配置相关
    'ASSETS_PERM_CACHE_TIME': 3600 * 24,
    'ASSETS_PERM_CACHE_ENABLE': HAS_XPACK,
    'PERM_SINGLE_ASSET_TO_UNGROUP_NODE': False,
    'PERM_EXPIRED_CHECK_PERIODIC': 60 * 60,

    # 任务相关
    ## Ansible 连接 windows 时的默认用的 shell
    'WINDOWS_SSH_DEFAULT_SHELL': 'cmd',
    'FLOWER_URL': "127.0.0.1:5555",
    'PERIOD_TASK_ENABLE': True,

    # 工单相关
    'TICKETS_ENABLED': True,
    'LOGIN_CONFIRM_ENABLE': False,

    # 监控相关
    'DISK_CHECK_ENABLED': True,

    # 自动改密相关
    'CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED': True,

    # 其他不过重要
    'DEFAULT_EXPIRED_YEARS': 70,
    'EMAIL_SUFFIX': 'jumpserver.org',
    'CAPTCHA_TEST_MODE': None,

    # 废弃的配置
    'ORG_CHANGE_TO_URL': '',
    'DEFAULT_ORG_SHOW_ALL_USERS': True,
    'DISPLAY_PER_PAGE': 15,
    'SESSION_EXPIRE_AT_BROWSER_CLOSE': False, # 已不再生效
    'AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS': False,
    'TERMINAL_HEARTBEAT_INTERVAL': 20,
}