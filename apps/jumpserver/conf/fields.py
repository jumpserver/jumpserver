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
        'type': 'str', 'label': _('LOG_LEVEL'), 'hidden': True,
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
        'default': os.path.join(PROJECT_DIR, 'logs'),
    },
    'LANGUAGE_CODE': 'zh',
    'TIME_ZONE': 'Asia/Shanghai',
    'SESSION_COOKIE_SECURE': False,
    'SESSION_SAVE_EVERY_REQUEST': True,
    'CSRF_COOKIE_DOMAIN': None,
    'CSRF_COOKIE_SECURE': False,
    'SESSION_COOKIE_DOMAIN': None,
    'BOOTSTRAP_TOKEN': {
        'type': 'str', 'label': _('BOOTSTRAP_TOKEN'),
        'hidden': True, 'required': True
    },
    'HTTP_BIND_HOST': '0.0.0.0',
    'HTTP_LISTEN_PORT': 8080,
    'WS_LISTEN_PORT': 8070,
    'FORCE_SCRIPT_NAME': '',

    # 数据库配置
    'DB_ENGINE': {
        'type': 'str', 'label': 'DB_ENGINE',
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
    'SITE_URL': {
        'type': 'str', 'label': _('Site url'), 'url': True,
        'required': True, 'default': 'http://localhost:8080'
    },
    'USER_GUIDE_URL': {
        'type': 'str', 'label': _('User guide url'), 'url': True,
        'required': False, 'allow_blank': True, 'allow_null': True, 'default': '',
        'help_text': _("User first login update profile done redirect to it")
    },
    'FORGOT_PASSWORD_URL': {
        'type': 'str', 'label': _('Forgot password url'), 'url': True,
        'required': False, 'allow_blank': True, 'allow_null': True, 'default': '',
        'help_text': _('The forgot password url on login page, If you use '
                       'ldap or cas external authentication, you can set it')
    },
    'GLOBAL_ORG_DISPLAY_NAME': {
        'type': 'str', 'label': _('Global organization name'),
        'required': False, 'allow_blank': True, 'allow_null': True, 'default': '',
        'help_text': _('The name of global organization to display')
    },

    # SMTP Settings
    'EMAIL_HOST': {
        'type': 'str', 'label': _('SMTP host'),
        'required': True
    },
    'EMAIL_PORT': {
        'type': 'str', 'label': _('SMTP port'),
        'required': True, 'max_length': 5
    },
    'EMAIL_HOST_USER': {
        'type': 'str', 'label': _('SMTP account'),
        'required': True
    },
    'EMAIL_HOST_PASSWORD': {
        'type': 'str', 'label': _('SMTP password'),
        'write_only': True, 'required': False,
        'help_text': _("Tips: Some provider use token except password")
    },
    'EMAIL_FROM': {
        'type': 'str', 'label': _('Send user'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips: Send mail account, default SMTP account as the send account')
    },
    'EMAIL_RECIPIENT': {
        'type': 'str', 'label': _('Test recipient'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips: Used only as a test mail recipient')
    },
    'EMAIL_USE_SSL': {
        'type': 'bool', 'label': _('Use SSL'),
        'required': False,
        'help_text': _('If SMTP port is 465, may be select')
    },
    'EMAIL_USE_TLS': {
        'type': 'bool', 'label': _('Use TLS'),
        'required': False,
        'help_text': _('If SMTP port is 587, may be select')
    },
    'EMAIL_SUBJECT_PREFIX': {
        'type': 'str', 'label': _('Subject prefix'),
        'required': True
    },
    'EMAIL_CUSTOM_USER_CREATED_SUBJECT': {
        'type': 'str', 'label': _('Create user email subject'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips: When creating a user, send the subject of the email '
                       '(eg:Create account successfully)')
    },
    'EMAIL_CUSTOM_USER_CREATED_HONORIFIC': {
        'type': 'str', 'label': _('Create user honorific'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips: When creating a user, send the honorific of the email (eg:Hello)')
    },
    'EMAIL_CUSTOM_USER_CREATED_BODY': {
        'type': 'str', 'label': _('Create user email content'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips:When creating a user, send the content of the email')
    },
    'EMAIL_CUSTOM_USER_CREATED_SIGNATURE': {
        'type': 'str', 'label': _('Signature'),
        'required': False, 'allow_blank': True,
        'help_text': _('Tips: Email signature (eg:jumpserver)')
    },

    # Custom Config
    # Auth LDAP Settings
    'AUTH_LDAP': {
        'type': 'bool', 'label': _('Enable LDAP auth'),
        'required': False, 'default': False
    },
    'AUTH_LDAP_SERVER_URI': {
        'type': 'str', 'label': _('LDAP server'),
        'required': True, 'default': 'http://localhost:8080',
        'help_text': _('eg: ldap://localhost:389')
    },
    'AUTH_LDAP_BIND_DN': {
        'type': 'str', 'label': _('Bind DN'),
        'required': False, 'default': 'cn=admin,dc=jumpserver,dc=org'
    },
    'AUTH_LDAP_BIND_PASSWORD': {
        'type': 'str', 'label': _('Password'),
        'required': False, 'default': '',
        'write_only': True
    },
    'AUTH_LDAP_SEARCH_OU': {
        'type': 'str', 'label': _('User OU'),
        'required': False, 'allow_blank': True, 'default': 'ou=tech,dc=jumpserver,dc=org',
        'help_text': _('Use | split multi OUs')
    },
    'AUTH_LDAP_SEARCH_FILTER': {
        'type': 'str', 'label': _('User search filter'),
        'required': True, 'default': '(cn=%(user)s)',
        'help_text': _('Choice may be (cn|uid|sAMAccountName)=%(user)s)')
    },
    'AUTH_LDAP_USER_ATTR_MAP': {
        'type': 'dict', 'label': _('User attr map'),
        'required': True, 'default': {"username": "cn", "name": "sn", "email": "mail"},
        'help_text': _(
            'User attr map present how to map LDAP user attr to jumpserver, username,name,email is jumpserver attr')
    },
    'AUTH_LDAP_START_TLS': False,
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
    'CAS_USERNAME_ATTRIBUTE': 'uid',
    'CAS_APPLY_ATTRIBUTES_TO_USER': False,
    'CAS_RENAME_ATTRIBUTES': {},
    'CAS_CREATE_USER': True,

    # 微信 认证
    'AUTH_WECOM': {
        'type': 'bool', 'label': _('Enable WeCom Auth'),
        'required': True, 'default': False
    },
    'WECOM_CORPID': {
        'type': 'str', 'label': 'corpid',
        'required': True, 'default': ''
    },
    'WECOM_AGENTID': {
        'type': 'str', 'label': 'agentid',
        'required': True, 'default': ''
    },
    'WECOM_SECRET': {
        'type': 'str', 'label': 'secret',
        'required': False, 'write_only': True, 'default': ''
    },

    # 钉钉 认证
    'AUTH_DINGTALK': {
        'type': 'bool', 'label': _('Enable DingTalk Auth'),
        'required': True, 'default': False
    },
    'DINGTALK_AGENTID': {
        'type': 'str', 'label': 'AgentId',
        'required': True, 'default': ''
    },
    'DINGTALK_APPKEY': {
        'type': 'str', 'label': 'AppKey',
        'required': True, 'default': ''
    },
    'DINGTALK_APPSECRET': {
        'type': 'str', 'label': 'AppSecret',
        'required': False, 'write_only': True, 'default': ''
    },

    # 飞书 认证
    'AUTH_FEISHU': {
        'type': 'bool', 'label': _('Enable FeiShu Auth'),
        'required': True, 'default': False
    },
    'FEISHU_APP_ID': {
        'type': 'str', 'label': 'App ID',
        'required': True, 'default': ''
    },
    'FEISHU_APP_SECRET': {
        'type': 'str', 'label': 'App Secret',
        'required': False, 'write_only': True, 'default': ''
    },

    # Terminal 相关配置
    'TERMINAL_PASSWORD_AUTH': {
        'type': 'bool', 'label': _('Password auth'),
        'required': False, 'default': True
    },
    'TERMINAL_PUBLIC_KEY_AUTH': {
        'type': 'bool', 'label': _('Public key auth'),
        'required': False, 'default': True,
        'help_text': _('Tips: If use other auth method, like AD/LDAP, you should disable this to '
                       'avoid being able to log in after deleting')
    },
    'TERMINAL_ASSET_LIST_SORT_BY': {
        'type': 'str', 'label': _('List sort by'),
        'choices': (
            ('hostname', _('Hostname')),
            ('ip', _('IP'))
        ),
        'required': False, 'default': 'hostname'
    },
    'TERMINAL_ASSET_LIST_PAGE_SIZE': {
        'type': 'str', 'label': _('List page size'),
        'choices': (
            ('all', _('All')),
            ('auto', _('Auto')),
            ('10', '10'),
            ('15', '15'),
            ('25', '25'),
            ('50', '50'),
        ),
        'required': False, 'default': 'auto'
    },
    'TERMINAL_SESSION_KEEP_DURATION': {
        'type': 'int', 'label': _('Session keep duration'),
        'required': True, 'default': 200, 'min_value': 1, 'max_value': 99999,
        'help_text': _('Units: days, Session, record, command will be delete if more than duration, only in database')
    },
    'TERMINAL_TELNET_REGEX': {
        'type': 'str', 'label': _('Telnet login regex'),
        'required': False, 'allow_blank': True, 'default': ''
    },
    'TERMINAL_RDP_ADDR': {
        'type': 'str', 'label': _('RDP address'),
        'required': False, 'allow_blank': True, 'default': '',
        'help_text': _('RDP visit address, eg: dev.jumpserver.org:3389')
    },
    'TERMINAL_HOST_KEY': '',
    'TERMINAL_COMMAND_STORAGE': {},
    'WINDOWS_SKIP_ALL_MANUAL_PASSWORD': False,
    'SERVER_REPLAY_STORAGE': {},

    # 安全相关配置
    'SECURITY_MFA_AUTH': {
        'type': 'str', 'label': _("Global MFA auth"),
        'choices': (
            (0, _('Disable')),
            (1, _('All users')),
            (2, _('Only admin users')),
        ),
        'required': False, 'default': False
    },
    'SECURITY_COMMAND_EXECUTION': {
        'type': 'bool', 'label': _('Batch command execution'),
        'required': False, 'default': True
    },
    'SECURITY_SERVICE_ACCOUNT_REGISTRATION': {
        'type': 'bool', 'label': _('Enable terminal register'),
        'required': True, 'default': True,
        'help_text': _('Allow terminal register, after all terminal setup, you should disable this for security')
    },
    'SECURITY_WATERMARK_ENABLED': {
        'type': 'bool', 'label': _('Replay watermark'),
        'required': True, 'default': True,
        'help_text': _('Enabled, the session replay contains watermark information')
    },
    'SECURITY_LOGIN_LIMIT_COUNT': {
        'type': 'int', 'label': _('Limit the number of login failures'),
        'default': 7, 'min_value': 3, 'max_value': 99999
    },
    'SECURITY_LOGIN_LIMIT_TIME': {
        'type': 'int', 'label': _('Block logon interval'),
        'required': True, 'default': 30, 'min_value': 5, 'max_value': 99999,
        'help_text': _('Tip: (unit/minute) if the user has failed to log in for a limited number of times, no login is allowed during this time interval.')
    },
    'SECURITY_MAX_IDLE_TIME': {
        'type': 'int', 'label': _('Connection max idle time'),
        'required': False, 'default': 30, 'min_value': 1, 'max_value': 99999,
        'help_text': _('If idle time more than it, disconnect connection Unit: minute')
    },
    'SECURITY_PASSWORD_EXPIRATION_TIME': {
        'type': 'int', 'label': _('User password expiration'),
        'required': True, 'default': 9999, 'min_value': 1, 'max_value': 99999,
        'help_text': _('Tip: (unit: day) If the user does not update the password during the time, the user password will expire failure;The password expiration reminder mail will be automatic sent to the user by system within 5 days (daily) before the password expires')
    },
    'OLD_PASSWORD_HISTORY_LIMIT_COUNT': {
        'type': 'int', 'label': _('Number of repeated historical passwords'),
        'required': True, 'default': 5, 'min_value': 0, 'max_value': 99999,
        'help_text': _('Tip: When the user resets the password, it cannot be the previous n historical passwords of the user')
    },
    'SECURITY_PASSWORD_MIN_LENGTH': {
        'type': 'int', 'label': _('Password minimum length'),
        'required': True, 'default': 6, 'min_value': 6, 'max_value': 30
    },
    'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH': {
        'type': 'int', 'label': _('Admin user password minimum length'),
        'required': True, 'default': 6, 'min_value': 6, 'max_value': 30
    },
    'SECURITY_PASSWORD_UPPER_CASE': {
        'type': 'bool', 'label': _('Must contain capital'),
        'required': False, 'default': False
    },
    'SECURITY_PASSWORD_LOWER_CASE': {
        'type': 'bool', 'label': _('Must contain lowercase'),
        'required': False, 'default': False
    },
    'SECURITY_PASSWORD_NUMBER': {
        'type': 'bool', 'label': _('Must contain numeric'),
        'required': False, 'default': False
    },
    'SECURITY_PASSWORD_SPECIAL_CHAR': {
        'type': 'bool', 'label': _('Must contain special'),
        'required': False, 'default': False
    },
    'SECURITY_INSECURE_COMMAND': {
        'type': 'bool', 'label': _('Insecure command alert'),
        'required': False, 'default': False
    },
    'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER': {
        'type': 'str', 'label': _('Email recipient'),
        'required': False, 'allow_blank': True, 'max_length': 8192, 'default': False,
        'help_text': _('Multiple user using , split')
    },
    'SECURITY_VIEW_AUTH_NEED_MFA': True,
    'SECURITY_LOGIN_CHALLENGE_ENABLED': False,
    'SECURITY_LOGIN_CAPTCHA_ENABLED': True,
    'SECURITY_INSECURE_COMMAND_LEVEL': 5,
    'SECURITY_MFA_VERIFY_TTL': 3600,
    'SECURITY_LUNA_REMEMBER_AUTH': True,
    'REFERER_CHECK_ENABLED': False,
    'SECURITY_DATA_CRYPTO_ALGO': 'aes',

    # 登录安全相关
    'CONNECTION_TOKEN_ENABLED': False,
    'ONLY_ALLOW_EXIST_USER_AUTH': False,
    'ONLY_ALLOW_AUTH_FROM_SOURCE': False,
    'SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE': False,
    'USER_LOGIN_SINGLE_MACHINE_ENABLED': False,
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
    # Ansible 连接 windows 时的默认用的 shell
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

    'HEALTH_CHECK_TOKEN': '',
    'LOGIN_REDIRECT_TO_BACKEND': None,  # 'OPENID / CAS
    'CLOUD_SYNC_TASK_EXECUTION_KEEP_DAYS': 30,

    # 废弃的配置
    'ORG_CHANGE_TO_URL': '',
    'DEFAULT_ORG_SHOW_ALL_USERS': True,
    'DISPLAY_PER_PAGE': 15,
    'SESSION_EXPIRE_AT_BROWSER_CLOSE': False,  # 已不再生效
    'AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS': False,
    'TERMINAL_HEARTBEAT_INTERVAL': 20,
}
