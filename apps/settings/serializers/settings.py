# coding: utf-8

from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import Setting

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
    encrypt_fields = ["EMAIL_HOST_PASSWORD", ]

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
    encrypt_fields = ["AUTH_LDAP_BIND_PASSWORD", ]

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
    TERMINAL_PASSWORD_AUTH = serializers.BooleanField(required=False)
    TERMINAL_PUBLIC_KEY_AUTH = serializers.BooleanField(required=False)
    TERMINAL_HEARTBEAT_INTERVAL = serializers.IntegerField(min_value=5, max_value=99999, required=False)
    TERMINAL_ASSET_LIST_SORT_BY = serializers.ChoiceField(SORT_BY_CHOICES, required=False)
    TERMINAL_ASSET_LIST_PAGE_SIZE = serializers.ChoiceField(PAGE_SIZE_CHOICES, required=False)
    TERMINAL_SESSION_KEEP_DURATION = serializers.IntegerField(min_value=1, max_value=99999, required=True)
    TERMINAL_TELNET_REGEX = serializers.CharField(allow_blank=True, required=False)


class SecuritySettingSerializer(serializers.Serializer):
    SECURITY_MFA_AUTH = serializers.BooleanField(required=False)
    SECURITY_COMMAND_EXECUTION = serializers.BooleanField(required=False)
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = serializers.BooleanField(required=True)
    SECURITY_LOGIN_LIMIT_COUNT = serializers.IntegerField(min_value=3, max_value=99999, required=True)
    SECURITY_LOGIN_LIMIT_TIME = serializers.IntegerField(min_value=5, max_value=99999, required=True)
    SECURITY_MAX_IDLE_TIME = serializers.IntegerField(min_value=1, max_value=99999, required=False)
    SECURITY_PASSWORD_EXPIRATION_TIME = serializers.IntegerField(min_value=1, max_value=99999, required=True)
    SECURITY_PASSWORD_MIN_LENGTH = serializers.IntegerField(min_value=6, max_value=30, required=True)
    SECURITY_PASSWORD_UPPER_CASE = serializers.BooleanField(required=False)
    SECURITY_PASSWORD_LOWER_CASE = serializers.BooleanField(required=False)
    SECURITY_PASSWORD_NUMBER = serializers.BooleanField(required=False)
    SECURITY_PASSWORD_SPECIAL_CHAR = serializers.BooleanField(required=False)
    SECURITY_INSECURE_COMMAND = serializers.BooleanField(required=False)
    SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER = serializers.CharField(max_length=8192, required=False, allow_blank=True)


class SettingsSerializer(
    BasicSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    LDAPSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer
):

    encrypt_fields = ["EMAIL_HOST_PASSWORD", "AUTH_LDAP_BIND_PASSWORD"]

    def create(self, validated_data):
        pass

    def _update(self, instance, validated_data):
        for category, category_data in validated_data.items():
            if not category_data:
                continue
            self.update_validated_settings(category_data)
            for field_name, field_value in category_data.items():
                setattr(getattr(instance, category), field_name, field_value)

        return instance

    def update_validated_settings(self, validated_data, category='default'):
        if not validated_data:
            return
        with transaction.atomic():
            for field_name, field_value in validated_data.items():
                try:
                    setting = Setting.objects.get(name=field_name)
                except Setting.DoesNotExist:
                    setting = Setting()
                encrypted = True if field_name in self.encrypt_fields else False
                setting.name = field_name
                setting.category = category
                setting.encrypted = encrypted
                setting.cleaned_value = field_value
                setting.save()
