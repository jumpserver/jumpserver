from django.utils.translation import ugettext_lazy as _

FIELDSET = [
    {
        'name': 'Django',
        'label': 'Django Config',
        'help_text': "Django internal Settings, before system start",
        'fields': [
            'SECRET_KEY', 'DEBUG', 'LOG_LEVEL', 'LOG_DIR',
            'LANGUAGE_CODE', 'TIME_ZONE',
            'SESSION_COOKIE_SECURE','SESSION_SAVE_EVERY_REQUEST', 'CSRF_COOKIE_DOMAIN',
            'BOOTSTRAP_TOKEN', 'FORCE_SCRIPT_NAME',
            'HTTP_BIND_HOST', 'HTTP_LISTEN_PORT', 'WS_LISTEN_PORT',
        ]
    },
    {
        'name': "Database",
        'label': "Database Settings",
        'fields': [
            'DB_ENGINE', 'DB_NAME', 'DB_HOST', 'DB_PORT',
            'DB_USER', 'DB_PASSWORD',
        ]
    },
    {
        'name': 'Redis',
        'label': 'Redis Settings',
        'fields': [
            'REDIS_HOST', 'REDIS_PORT', 'REDIS_PASSWORD',
            'REDIS_DB_CACHE', 'REDIS_DB_CELERY', 'REDIS_DB_SESSION', 'REDIS_DB_WS',
        ]
    },
    {
        'name': 'Generic',
        'label': _('Generic Settings'),
        'fields': [
            'SITE_URL', 'USER_GUIDE_URL',
        ]
    },
    {
        'name': 'SMTP_SETTING',
        'label': _('SMTP Setting'),
        'fields': [
            'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD', 'EMAIL_FROM',
            'EMAIL_RECIPIENT', 'EMAIL_USE_SSL', 'EMAIL_USE_TLS', 'EMAIL_SUBJECT_PREFIX'
        ]
    },
    {
        'name': 'AUTH_LDAP',
        'label': _('Auth LDAP Settings'),
        'fields': [
            'AUTH_LDAP', 'AUTH_LDAP_SERVER_URI', 'AUTH_LDAP_BIND_DN',
            'AUTH_LDAP_BIND_PASSWORD', 'AUTH_LDAP_SEARCH_OU', 'AUTH_LDAP_SEARCH_FILTER',
            'AUTH_LDAP_START_TLS', 'AUTH_LDAP_USER_ATTR_MAP', 'AUTH_LDAP_CONNECT_TIMEOUT',
            'AUTH_LDAP_OPTIONS_OPT_REFERRALS',
            'AUTH_LDAP_SEARCH_PAGED_SIZE', 'AUTH_LDAP_SYNC_IS_PERIODIC',
            'AUTH_LDAP_SYNC_INTERVAL', 'AUTH_LDAP_SYNC_CRONTAB'
        ]
    },
    {
        'name': 'AUTH_OIDC',
        'label': _('Auth OIDC Settings'),
        'fields': [
            'AUTH_OPENID', 'BASE_SITE_URL',
            'AUTH_OPENID_CLIENT_ID', 'AUTH_OPENID_CLIENT_SECRET',
            'AUTH_OPENID_PROVIDER_ENDPOINT', 'AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT',
            'AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT', 'AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT',
            'AUTH_OPENID_PROVIDER_JWKS_ENDPOINT', 'AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT',
            'AUTH_OPENID_PROVIDER_SIGNATURE_ALG', 'AUTH_OPENID_PROVIDER_SIGNATURE_KEY',
            'AUTH_OPENID_SCOPES', 'AUTH_OPENID_ID_TOKEN_MAX_AGE',
            'AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS', 'AUTH_OPENID_USE_STATE',
            'AUTH_OPENID_USE_NONCE', 'AUTH_OPENID_ALWAYS_UPDATE_USER',
            'AUTH_OPENID_SHARE_SESSION', 'AUTH_OPENID_IGNORE_SSL_VERIFICATION',
        ]
    },
    {
        'name': 'AUTH_KEYCLOAK',
        'label': _('Auth Keycloak Settings'),
        'fields': [
            'AUTH_OPENID', 'BASE_SITE_URL',
            'AUTH_OPENID_CLIENT_ID', 'AUTH_OPENID_CLIENT_SECRET',
            'AUTH_OPENID_SHARE_SESSION', 'AUTH_OPENID_IGNORE_SSL_VERIFICATION',
            'AUTH_OPENID_SERVER_URL', 'AUTH_OPENID_REALM_NAME',
        ]
    },
    {
        'name': 'AUTH_RADIUS',
        'label': _('Auth Radius Setting'),
        'fields': [
            'AUTH_RADIUS', 'RADIUS_SERVER', 'RADIUS_PORT', 'RADIUS_SECRET',
            'RADIUS_ENCRYPT_PASSWORD', 'OTP_IN_RADIUS',
        ]
    },
    {
        'name': 'AUTH_CAS',
        'label': _('Auth CAS Setting'),
        'fields': [
            'AUTH_CAS', 'CAS_SERVER_URL', 'CAS_ROOT_PROXIED_AS',
            'CAS_LOGOUT_COMPLETELY', 'CAS_VERSION',
        ]
    },
    {
        'name': 'TERMINAL_SETTINGS',
        'label': _('Terminal Setting'),
        'fields': [
            'TERMINAL_PASSWORD_AUTH', 'TERMINAL_PUBLIC_KEY_AUTH',
            'TERMINAL_ASSET_LIST_SORT_BY', 'TERMINAL_ASSET_LIST_PAGE_SIZE',
            'TERMINAL_SESSION_KEEP_DURATION', 'TERMINAL_HOST_KEY',
            'TERMINAL_TELNET_REGEX', 'TERMINAL_COMMAND_STORAGE',
            'WINDOWS_SKIP_ALL_MANUAL_PASSWORD', 'SERVER_REPLAY_STORAGE'
        ]
    },
    {
        'name': 'SECURITY_SETTINGS',
        'label': _('Security Setting'),
        'fields': [
            'SECURITY_MFA_AUTH', 'SECURITY_COMMAND_EXECUTION',
            'SECURITY_SERVICE_ACCOUNT_REGISTRATION',
            'SECURITY_LOGIN_LIMIT_COUNT', 'SECURITY_LOGIN_LIMIT_TIME',
            'SECURITY_MAX_IDLE_TIME', 'SECURITY_PASSWORD_EXPIRATION_TIME',
            # 登录验证码，还是 MFA
            'SECURITY_LOGIN_CHALLENGE_ENABLED', 'SECURITY_LOGIN_CAPTCHA_ENABLED',
            # 命令告警
            'SECURITY_INSECURE_COMMAND', 'SECURITY_INSECURE_COMMAND_LEVEL',
            'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER',
            # 查看密码
            'SECURITY_VIEW_AUTH_NEED_MFA', 'SECURITY_MFA_VERIFY_TTL',
        ]
    },
    {
        'name': "SECURITY_PASSWORD_STRATEGY",
        'label': _('Security Password Strategy'),
        'fields': [
            'SECURITY_PASSWORD_MIN_LENGTH', 'SECURITY_PASSWORD_UPPER_CASE',
            'SECURITY_PASSWORD_LOWER_CASE', 'SECURITY_PASSWORD_NUMBER',
            'SECURITY_PASSWORD_SPECIAL_CHAR',
        ]
    },
    {
        'name': "LOGIN_SECURITY",
        'label': _("Login Security Setting"),
        'fields': [
            'CONNECTION_TOKEN_ENABLED',
            'ONLY_ALLOW_EXIST_USER_AUTH', 'ONLY_ALLOW_AUTH_FROM_SOURCE',
            'SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE', 'SESSION_COOKIE_AGE',
            'USER_LOGIN_SINGLE_MACHINE_ENABLED', 'FORGOT_PASSWORD_URL',
            'TOKEN_EXPIRATION',
            'OTP_VALID_WINDOW', 'OTP_ISSUER_NAME',
            'AUTH_SSO', 'AUTH_SSO_AUTHKEY_TTL'
        ]
    },
    {
        'name': 'LOG_SETTING',
        'label': 'Log settings',
        'fields': [
            'LOGIN_LOG_KEEP_DAYS', 'TASK_LOG_KEEP_DAYS',
            'OPERATE_LOG_KEEP_DAYS', 'FTP_LOG_KEEP_DAYS',
            # syslog配置
            'SYSLOG_ENABLE', 'SYSLOG_ADDR', 'SYSLOG_FACILITY', 'SYSLOG_SOCKTYPE'
        ]
    },
    {
        'name': 'OTHER_SETTING',
        'label': 'Other settings',
        'fields': [
            'WINDOWS_SSH_DEFAULT_SHELL', 'FLOWER_URL', 'PERIOD_TASK_ENABLE',
            'TICKETS_ENABLED', 'LOGIN_CONFIRM_ENABLE', 'DISK_CHECK_ENABLED',
            'DEFAULT_EXPIRED_YEARS', 'EMAIL_SUFFIX', 'CHANGE_AUTH_PLAN_SECURE_MODE_ENABLED',
        ]
    }
]