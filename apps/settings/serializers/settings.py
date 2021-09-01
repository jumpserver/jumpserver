# coding: utf-8

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = [
    'BasicSettingSerializer', 'EmailSettingSerializer', 'EmailContentSettingSerializer',
    'LDAPSettingSerializer', 'TerminalSettingSerializer', 'SecuritySettingSerializer',
    'SettingsSerializer', 'WeComSettingSerializer', 'DingTalkSettingSerializer',
    'FeiShuSettingSerializer', 'SeniorSettingSerializer'
]


class BasicSettingSerializer(serializers.Serializer):
    SITE_URL = serializers.URLField(
        required=True, label=_("Site url"),
        help_text=_('eg: http://dev.jumpserver.org:8080')
    )

    USER_GUIDE_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("User guide url"),
        help_text=_('User first login update profile done redirect to it')
    )
    FORGOT_PASSWORD_URL = serializers.URLField(
        required=False, allow_blank=True, allow_null=True, label=_("Forgot password url"),
        help_text=_('The forgot password url on login page, If you use '
                    'ldap or cas external authentication, you can set it')
    )
    GLOBAL_ORG_DISPLAY_NAME = serializers.CharField(
        required=False, max_length=1024, allow_blank=True, allow_null=True, label=_("Global organization name"),
        help_text=_('The name of global organization to display')
    )


class EmailSettingSerializer(serializers.Serializer):
    # encrypt_fields 现在使用 write_only 来判断了

    EMAIL_HOST = serializers.CharField(max_length=1024, required=True, label=_("SMTP host"))
    EMAIL_PORT = serializers.CharField(max_length=5, required=True, label=_("SMTP port"))
    EMAIL_HOST_USER = serializers.CharField(max_length=128, required=True, label=_("SMTP account"))
    EMAIL_HOST_PASSWORD = serializers.CharField(
        max_length=1024, write_only=True, required=False, label=_("SMTP password"),
        help_text=_("Tips: Some provider use token except password")
    )
    EMAIL_FROM = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Send user'),
        help_text=_('Tips: Send mail account, default SMTP account as the send account')
    )
    EMAIL_RECIPIENT = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Test recipient'),
        help_text=_('Tips: Used only as a test mail recipient')
    )
    EMAIL_USE_SSL = serializers.BooleanField(
        required=False, label=_('Use SSL'),
        help_text=_('If SMTP port is 465, may be select')
    )
    EMAIL_USE_TLS = serializers.BooleanField(
        required=False, label=_("Use TLS"),
        help_text=_('If SMTP port is 587, may be select')
    )
    EMAIL_SUBJECT_PREFIX = serializers.CharField(
        max_length=1024, required=True, label=_('Subject prefix')
    )


class EmailContentSettingSerializer(serializers.Serializer):
    EMAIL_CUSTOM_USER_CREATED_SUBJECT = serializers.CharField(
        max_length=1024, allow_blank=True, required=False,
        label=_('Create user email subject'),
        help_text=_('Tips: When creating a user, send the subject of the email (eg:Create account successfully)')
    )
    EMAIL_CUSTOM_USER_CREATED_HONORIFIC = serializers.CharField(
        max_length=1024, allow_blank=True, required=False,
        label=_('Create user honorific'),
        help_text=_('Tips: When creating a user, send the honorific of the email (eg:Hello)')
    )
    EMAIL_CUSTOM_USER_CREATED_BODY = serializers.CharField(
        max_length=4096, allow_blank=True, required=False,
        label=_('Create user email content'),
        help_text=_('Tips:When creating a user, send the content of the email')
    )
    EMAIL_CUSTOM_USER_CREATED_SIGNATURE = serializers.CharField(
        max_length=512, allow_blank=True, required=False, label=_('Signature'),
        help_text=_('Tips: Email signature (eg:jumpserver)')
    )


class LDAPSettingSerializer(serializers.Serializer):
    # encrypt_fields 现在使用 write_only 来判断了

    AUTH_LDAP_SERVER_URI = serializers.CharField(
        required=True, max_length=1024, label=_('LDAP server'), help_text=_('eg: ldap://localhost:389')
    )
    AUTH_LDAP_BIND_DN = serializers.CharField(required=False, max_length=1024, label=_('Bind DN'))
    AUTH_LDAP_BIND_PASSWORD = serializers.CharField(max_length=1024, write_only=True, required=False,
                                                    label=_('Password'))
    AUTH_LDAP_SEARCH_OU = serializers.CharField(
        max_length=1024, allow_blank=True, required=False, label=_('User OU'),
        help_text=_('Use | split multi OUs')
    )
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField(
        max_length=1024, required=True, label=_('User search filter'),
        help_text=_('Choice may be (cn|uid|sAMAccountName)=%(user)s)')
    )
    AUTH_LDAP_USER_ATTR_MAP = serializers.DictField(
        required=True, label=_('User attr map'),
        help_text=_(
            'User attr map present how to map LDAP user attr to jumpserver, username,name,email is jumpserver attr')
    )
    AUTH_LDAP = serializers.BooleanField(required=False, label=_('Enable LDAP auth'))


class TerminalSettingSerializer(serializers.Serializer):
    SORT_BY_CHOICES = (
        ('hostname', _('Hostname')),
        ('ip', _('IP'))
    )

    PAGE_SIZE_CHOICES = (
        ('all', _('All')),
        ('auto', _('Auto')),
        ('10', '10'),
        ('15', '15'),
        ('25', '25'),
        ('50', '50'),
    )
    TERMINAL_PASSWORD_AUTH = serializers.BooleanField(required=False, label=_('Password auth'))
    TERMINAL_PUBLIC_KEY_AUTH = serializers.BooleanField(
        required=False, label=_('Public key auth'),
        help_text=_('Tips: If use other auth method, like AD/LDAP, you should disable this to '
                    'avoid being able to log in after deleting')
    )
    TERMINAL_ASSET_LIST_SORT_BY = serializers.ChoiceField(SORT_BY_CHOICES, required=False, label=_('List sort by'))
    TERMINAL_ASSET_LIST_PAGE_SIZE = serializers.ChoiceField(PAGE_SIZE_CHOICES, required=False,
                                                            label=_('List page size'))
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=1, max_value=99999, required=True, label=_('Session keep duration'),
        help_text=_('Units: days, Session, record, command will be delete if more than duration, only in database')
    )
    TERMINAL_TELNET_REGEX = serializers.CharField(allow_blank=True, max_length=1024, required=False,
                                                  label=_('Telnet login regex'))
    TERMINAL_RDP_ADDR = serializers.CharField(
        required=False, label=_("RDP address"),
        max_length=1024,
        allow_blank=True,
        help_text=_('RDP visit address, eg: dev.jumpserver.org:3389')
    )


class SecuritySettingSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.ChoiceField(
        choices=(
            [0, _('Disable')],
            [1, _('All users')],
            [2, _('Only admin users')],
        ),
        required=False, label=_("Global MFA auth")
    )
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Batch command execution'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(
        required=True, label=_('Enable terminal register'),
        help_text=_("Allow terminal register, after all terminal setup, you should disable this for security")
    )
    SECURITY_WATERMARK_ENABLED = serializers.BooleanField(
        required=True, label=_('Replay watermark'),
        help_text=_('Enabled, the session replay contains watermark information')
    )
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Limit the number of login failures')
    )
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Block logon interval'),
        help_text=_(
            'Tip: (unit/minute) if the user has failed to log in for a limited number of times, no login is allowed during this time interval.')
    )
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Connection max idle time'),
        help_text=_('If idle time more than it, disconnect connection Unit: minute')
    )
    SECURITY_PASSWORD_EXPIRATION_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('User password expiration'),
        help_text=_(
            'Tip: (unit: day) If the user does not update the password during the time, the user password will expire failure;The password expiration reminder mail will be automatic sent to the user by system within 5 days (daily) before the password expires')
    )
    OLD_PASSWORD_HISTORY_LIMIT_COUNT = serializers.IntegerField(
        min_value=0, max_value=99999, required=True,
        label=_('Number of repeated historical passwords'),
        help_text=_(
            'Tip: When the user resets the password, it cannot be the previous n historical passwords of the user')
    )
    SECURITY_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Password minimum length')
    )
    SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Admin user password minimum length')
    )
    SECURITY_PASSWORD_UPPER_CASE = serializers.BooleanField(
        required=False, label=_('Must contain capital')
    )
    SECURITY_PASSWORD_LOWER_CASE = serializers.BooleanField(required=False, label=_('Must contain lowercase'))
    SECURITY_PASSWORD_NUMBER = serializers.BooleanField(required=False, label=_('Must contain numeric'))
    SECURITY_PASSWORD_SPECIAL_CHAR = serializers.BooleanField(required=False, label=_('Must contain special'))
    SECURITY_INSECURE_COMMAND = serializers.BooleanField(required=False, label=_('Insecure command alert'))
    SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER = serializers.CharField(
        max_length=8192, required=False, allow_blank=True, label=_('Email recipient'),
        help_text=_('Multiple user using , split')
    )


class WeComSettingSerializer(serializers.Serializer):
    WECOM_CORPID = serializers.CharField(max_length=256, required=True, label='corpid')
    WECOM_AGENTID = serializers.CharField(max_length=256, required=True, label='agentid')
    WECOM_SECRET = serializers.CharField(max_length=256, required=False, label='secret', write_only=True)
    AUTH_WECOM = serializers.BooleanField(default=False, label=_('Enable WeCom Auth'))


class DingTalkSettingSerializer(serializers.Serializer):
    DINGTALK_AGENTID = serializers.CharField(max_length=256, required=True, label='AgentId')
    DINGTALK_APPKEY = serializers.CharField(max_length=256, required=True, label='AppKey')
    DINGTALK_APPSECRET = serializers.CharField(max_length=256, required=False, label='AppSecret', write_only=True)
    AUTH_DINGTALK = serializers.BooleanField(default=False, label=_('Enable DingTalk Auth'))


class FeiShuSettingSerializer(serializers.Serializer):
    FEISHU_APP_ID = serializers.CharField(max_length=256, required=True, label='App ID')
    FEISHU_APP_SECRET = serializers.CharField(max_length=256, required=False, label='App Secret', write_only=True)
    AUTH_FEISHU = serializers.BooleanField(default=False, label=_('Enable FeiShu Auth'))


class SeniorSettingSerializer(serializers.Serializer):
    AUTH_LDAP_CONNECT_TIMEOUT = serializers.IntegerField(required=False, label=_('Connect timeout'))
    AUTH_LDAP_SEARCH_PAGED_SIZE = serializers.IntegerField(required=False, label=_('Search paged size'))
    AUTH_LDAP_SYNC_IS_PERIODIC = serializers.BooleanField(required=False, label=_('Periodic display'))
    AUTH_LDAP_SYNC_INTERVAL = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Interval'))
    AUTH_LDAP_SYNC_CRONTAB = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Regularly perform'))
    AUTH_LDAP_USER_LOGIN_ONLY_IN_USERS = serializers.BooleanField(required=False, label=_('User login only in users'))

    # OpenID 公有配置参数 (version <= 1.5.8 或 version >= 1.5.8)
    AUTH_OPENID = serializers.BooleanField(required=False, label=_('Enable OPENID Auth'))
    BASE_SITE_URL = serializers.CharField(
        required=False, allow_null=True, max_length=1024, label=_('Base site url'))
    AUTH_OPENID_CLIENT_ID = serializers.CharField(required=False, max_length=1024, label=_('Client Id'))
    AUTH_OPENID_CLIENT_SECRET = serializers.CharField(required=False, max_length=1024, label=_('Client Secret'))
    AUTH_OPENID_SHARE_SESSION = serializers.BooleanField(required=False, label=_('Share session'))
    AUTH_OPENID_IGNORE_SSL_VERIFICATION = serializers.BooleanField(required=False, label=_('Ignore ssl verification'))

    # OpenID 新配置参数 (version >= 1.5.9)
    AUTH_OPENID_PROVIDER_ENDPOINT = serializers.CharField(required=False, max_length=1024, label=_('Provider endpoint'))
    AUTH_OPENID_PROVIDER_AUTHORIZATION_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider auth endpoint'))
    AUTH_OPENID_PROVIDER_TOKEN_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider token endpoint'))
    AUTH_OPENID_PROVIDER_JWKS_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider jwk endpoint'))
    AUTH_OPENID_PROVIDER_USERINFO_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider userinfo endpoint'))
    AUTH_OPENID_PROVIDER_END_SESSION_ENDPOINT = serializers.CharField(
        required=False, max_length=1024, label=_('Provider end session endpoint'))
    AUTH_OPENID_PROVIDER_SIGNATURE_ALG = serializers.CharField(
        required=False, max_length=1024, label=_('Provider sign alg'))
    AUTH_OPENID_PROVIDER_SIGNATURE_KEY = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Provider sign key'))
    AUTH_OPENID_SCOPES = serializers.CharField(required=False, max_length=1024, label=_('Scopes'))
    AUTH_OPENID_ID_TOKEN_MAX_AGE = serializers.IntegerField(required=False, label=_('Id token max age'))
    AUTH_OPENID_ID_TOKEN_INCLUDE_CLAIMS = serializers.BooleanField(required=False, label=_('Id token include claims'))
    AUTH_OPENID_USE_STATE = serializers.BooleanField(required=False, label=_('Use state'))
    AUTH_OPENID_USE_NONCE = serializers.BooleanField(required=False, label=_('Use nonce'))
    AUTH_OPENID_ALWAYS_UPDATE_USER = serializers.BooleanField(required=False, label=_('Always update user'))
    # OpenID 旧配置参数 (version <= 1.5.8 (discarded))
    AUTH_OPENID_SERVER_URL = serializers.CharField(required=False, max_length=1024, label=_('Server url'))
    AUTH_OPENID_REALM_NAME = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Realm name'))

    AUTH_RADIUS = serializers.BooleanField(required=False, label=_('Enable RADIUS Auth'))
    RADIUS_SERVER = serializers.CharField(required=False, max_length=1024, label=_('Host'))
    RADIUS_PORT = serializers.IntegerField(required=False, label=_('Port'))
    RADIUS_SECRET = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Secret'), write_only=True)
    RADIUS_ENCRYPT_PASSWORD = serializers.BooleanField(required=False, label=_('Encrypt password'))
    OTP_IN_RADIUS = serializers.BooleanField(required=False, label=_('Otp in radius'))

    AUTH_CAS = serializers.BooleanField(required=False, label=_('Enable CAS Auth'))
    CAS_SERVER_URL = serializers.CharField(required=False, max_length=1024, label=_('Server url'))
    CAS_LOGOUT_COMPLETELY = serializers.BooleanField(required=False, label=_('Logout completely'))
    CAS_VERSION = serializers.IntegerField(required=False, label=_('Version'))
    CAS_USERNAME_ATTRIBUTE = serializers.CharField(required=False, max_length=1024, label=_('Username attr'))
    CAS_APPLY_ATTRIBUTES_TO_USER = serializers.BooleanField(required=False, label=_('Apply attr to use'))
    CAS_RENAME_ATTRIBUTES = serializers.DictField(required=False, label=_('Rename attr'))
    CAS_CREATE_USER = serializers.BooleanField(required=False, label=_('Create User'))

    AUTH_SSO = serializers.BooleanField(required=False, label=_('Enable SSO Auth'))
    AUTH_SSO_AUTHKEY_TTL = serializers.IntegerField(required=False, label=_('SSO authkey ttl'))
    OTP_VALID_WINDOW = serializers.IntegerField(required=False, label=_('OTP valid window'))
    OTP_ISSUER_NAME = serializers.CharField(required=False, max_length=1024, label=_('OTP issuer name'))
    SECURITY_LOGIN_CHALLENGE_ENABLED = serializers.BooleanField(required=False, label=_('Login challenge enabled'))
    SECURITY_LOGIN_CAPTCHA_ENABLED = serializers.BooleanField(required=False, label=_('Login captcha enabled'))
    SECURITY_INSECURE_COMMAND_LEVEL = serializers.IntegerField(required=False, label=_('Insecure command level'))


class SettingsSerializer(
    BasicSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    LDAPSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer,
    WeComSettingSerializer,
    DingTalkSettingSerializer,
    FeiShuSettingSerializer,
    SeniorSettingSerializer,
):
    # encrypt_fields 现在使用 write_only 来判断了
    pass
