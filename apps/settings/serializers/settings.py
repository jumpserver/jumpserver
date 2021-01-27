# coding: utf-8

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = [
    'BasicSettingSerializer', 'EmailSettingSerializer', 'EmailContentSettingSerializer',
    'LDAPSettingSerializer', 'TerminalSettingSerializer', 'SecuritySettingSerializer',
    'SettingsSerializer'
]


class BasicSettingSerializer(serializers.Serializer):
    SITE_URL = serializers.URLField(
        required=True, label=_("Site url"),
        help_text=_('eg: http://demo.jumpserver.org:8080')
    )
    USER_GUIDE_URL = serializers.URLField(
        required=False, allow_blank=True, label=_("User guide url"),
        help_text=_('User first login update profile done redirect to it')
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
        required=False,  label=_('Use SSL'),
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
    AUTH_LDAP_BIND_PASSWORD = serializers.CharField(max_length=1024, write_only=True, required=False, label=_('Password'))
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
        help_text=_('User attr map present how to map LDAP user attr to jumpserver, username,name,email is jumpserver attr')
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
    TERMINAL_PUBLIC_KEY_AUTH = serializers.BooleanField(required=False, label=_('Public key auth'))
    TERMINAL_ASSET_LIST_SORT_BY = serializers.ChoiceField(SORT_BY_CHOICES, required=False, label=_('List sort by'))
    TERMINAL_ASSET_LIST_PAGE_SIZE = serializers.ChoiceField(PAGE_SIZE_CHOICES, required=False, label=_('List page size'))
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(
        min_value=1, max_value=99999, required=True, label=_('Session keep duration'),
        help_text=_('Units: days, Session, record, command will be delete if more than duration, only in database')
    )
    TERMINAL_TELNET_REGEX = serializers.CharField(allow_blank=True, max_length=1024, required=False, label=_('Telnet login regex'))


class SecuritySettingSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.BooleanField(
        required=False, label=_("Global MFA auth"),
        help_text=_('All user enable MFA')
    )
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(
        required=False, label=_('Batch command execution'),
        help_text=_('Allow user run batch command or not using ansible')
    )
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(
        required=True, label=_('Enable terminal register'),
        help_text=_("Allow terminal register, after all terminal setup, you should disable this for security")
    )
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(
        min_value=3, max_value=99999,
        label=_('Limit the number of login failures')
    )
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(
        min_value=5, max_value=99999, required=True,
        label=_('Block logon interval'),
        help_text=_('Tip: (unit/minute) if the user has failed to log in for a limited number of times, no login is allowed during this time interval.')
    )
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_('Connection max idle time'),
        help_text=_('If idle time more than it, disconnect connection Unit: minute')
    )
    SECURITY_PASSWORD_EXPIRATION_TIME = serializers.IntegerField(
        min_value=1, max_value=99999, required=True,
        label=_('User password expiration'),
        help_text=_('Tip: (unit: day) If the user does not update the password during the time, the user password will expire failure;The password expiration reminder mail will be automatic sent to the user by system within 5 days (daily) before the password expires')
    )
    SECURITY_PASSWORD_MIN_LENGTH = serializers.IntegerField(
        min_value=6, max_value=30, required=True,
        label=_('Password minimum length')
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


class SettingsSerializer(
    BasicSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    LDAPSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer
):

    # encrypt_fields 现在使用 write_only 来判断了
    pass

