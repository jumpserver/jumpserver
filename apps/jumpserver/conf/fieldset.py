from django.utils.translation import ugettext_lazy as _

FIELDSET = {
    'Basic': {
        'label': 'Basic Settings',
        'fields': [
            'SITE_URL', 'USER_GUIDE_URL', 'FORGOT_PASSWORD_URL', 'GLOBAL_ORG_DISPLAY_NAME'
        ]
    },
    'Email': {
        'label': 'Email Settings',
        'fields': [
            'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD',
            'EMAIL_FROM', 'EMAIL_RECIPIENT', 'EMAIL_USE_SSL', 'EMAIL_USE_TLS', 'EMAIL_SUBJECT_PREFIX'
        ]
    },
    'Email_Content': {
        'label': 'EmailContent Settings',
        'fields': [
            'EMAIL_CUSTOM_USER_CREATED_SUBJECT', 'EMAIL_CUSTOM_USER_CREATED_HONORIFIC',
            'EMAIL_CUSTOM_USER_CREATED_BODY', 'EMAIL_CUSTOM_USER_CREATED_SIGNATURE'
        ]
    },
    'Ldap': {
        'label': 'Ldap Settings',
        'fields': [
            'AUTH_LDAP', 'AUTH_LDAP_SERVER_URI', 'AUTH_LDAP_BIND_DN', 'AUTH_LDAP_BIND_PASSWORD',
            'AUTH_LDAP_SEARCH_OU', 'AUTH_LDAP_SEARCH_FILTER', 'AUTH_LDAP_USER_ATTR_MAP'
        ]
    },
    'Wecom': {
        'label': 'Wecom Settings',
        'fields': [
            'AUTH_WECOM', 'WECOM_CORPID', 'WECOM_AGENTID', 'WECOM_SECRET'
        ]
    },
    'Dingtalk': {
        'label': 'Dingtalk Settings',
        'fields': [
            'AUTH_DINGTALK', 'DINGTALK_AGENTID', 'DINGTALK_APPKEY', 'DINGTALK_APPSECRET'
        ]
    },
    'Feishu': {
        'label': 'Feishu Settings',
        'fields': [
            'AUTH_FEISHU', 'FEISHU_APP_ID', 'FEISHU_APP_SECRET'
        ]
    },
    'Terminal': {
        'label': 'Terminal Settings',
        'fields': [
            'TERMINAL_PASSWORD_AUTH', 'TERMINAL_PUBLIC_KEY_AUTH', 'TERMINAL_ASSET_LIST_SORT_BY',
            'TERMINAL_ASSET_LIST_PAGE_SIZE', 'TERMINAL_SESSION_KEEP_DURATION', 'TERMINAL_TELNET_REGEX',
            'TERMINAL_RDP_ADDR'
        ]
    },
    'Security': {
        'label': 'Security Settings',
        'fields': [
            'SECURITY_MFA_AUTH', 'SECURITY_COMMAND_EXECUTION', 'SECURITY_SERVICE_ACCOUNT_REGISTRATION',
            'SECURITY_WATERMARK_ENABLED', 'SECURITY_LOGIN_LIMIT_COUNT', 'SECURITY_LOGIN_LIMIT_TIME',
            'SECURITY_MAX_IDLE_TIME', 'SECURITY_PASSWORD_EXPIRATION_TIME', 'OLD_PASSWORD_HISTORY_LIMIT_COUNT',
            'SECURITY_PASSWORD_MIN_LENGTH', 'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH', 'SECURITY_PASSWORD_UPPER_CASE',
            'SECURITY_PASSWORD_LOWER_CASE', 'SECURITY_PASSWORD_NUMBER', 'SECURITY_PASSWORD_SPECIAL_CHAR',
            'SECURITY_INSECURE_COMMAND', 'SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER'
        ]
    }
}