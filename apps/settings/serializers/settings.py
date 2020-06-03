# coding: utf-8

from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from ..models import Setting

__all__ = ['SettingsSerializer']


class BasicSettingSerializer(serializers.Serializer):
    SITE_URL = serializers.URLField(required=True)
    USER_GUIDE_URL = serializers.URLField(required=False, allow_blank=True, )
    EMAIL_SUBJECT_PREFIX = serializers.CharField(max_length=1024, required=True)


class EmailSettingSerializer(serializers.Serializer):
    encrypt_fields = ["EMAIL_HOST_PASSWORD", ]

    EMAIL_HOST = serializers.CharField(max_length=1024, required=True)
    EMAIL_PORT = serializers.CharField(max_length=5, required=True)
    EMAIL_HOST_USER = serializers.CharField(max_length=128, required=True)
    EMAIL_HOST_PASSWORD = serializers.CharField(max_length=1024, write_only=True, required=False, )
    EMAIL_FROM = serializers.CharField(max_length=128, allow_blank=True, required=False)
    EMAIL_RECIPIENT = serializers.CharField(max_length=128, allow_blank=True, required=False)
    EMAIL_USE_SSL = serializers.BooleanField(required=False)
    EMAIL_USE_TLS = serializers.BooleanField(required=False)


class EmailContentSettingSerializer(serializers.Serializer):
    EMAIL_CUSTOM_USER_CREATED_SUBJECT = serializers.CharField(max_length=1024, allow_blank=True, required=False, )
    EMAIL_CUSTOM_USER_CREATED_HONORIFIC = serializers.CharField(max_length=1024, allow_blank=True, required=False, )
    EMAIL_CUSTOM_USER_CREATED_BODY = serializers.CharField(max_length=4096, allow_blank=True, required=False)
    EMAIL_CUSTOM_USER_CREATED_SIGNATURE = serializers.CharField(max_length=512, allow_blank=True, required=False)


class LdapSettingSerializer(serializers.Serializer):
    encrypt_fields = ["AUTH_LDAP_BIND_PASSWORD", ]

    AUTH_LDAP_SERVER_URI = serializers.CharField(required=True)
    AUTH_LDAP_BIND_DN = serializers.CharField(required=False)
    AUTH_LDAP_BIND_PASSWORD = serializers.CharField(max_length=1024, write_only=True, required=False)
    AUTH_LDAP_SEARCH_OU = serializers.CharField(max_length=1024, allow_blank=True, required=False)
    AUTH_LDAP_SEARCH_FILTER = serializers.CharField(max_length=1024, required=True)
    AUTH_LDAP_USER_ATTR_MAP = serializers.DictField(required=True)
    AUTH_LDAP = serializers.BooleanField(required=False)


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
    TERMINAL_HEARTBEAT_INTERVAL = serializers.IntegerField(min_value=5, max_value=99999, required=True)
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


class SettingsSerializer(serializers.Serializer):
    basic = BasicSettingSerializer(required=False)
    email = EmailSettingSerializer(required=False)
    email_content = EmailContentSettingSerializer(required=False)
    ldap = LdapSettingSerializer(required=False)
    terminal = TerminalSettingSerializer(required=False)
    security = SecuritySettingSerializer(required=False)

    encrypt_fields = ["EMAIL_HOST_PASSWORD", "AUTH_LDAP_BIND_PASSWORD"]

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
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
