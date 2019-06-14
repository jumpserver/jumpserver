# -*- coding: utf-8 -*-
#
import json
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db import transaction

from .models import Setting, settings
from common.fields import (
    FormDictField, FormEncryptCharField, FormEncryptMixin
)


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            value = getattr(settings, name, None)
            if value is None:  # and django_value is None:
                continue

            if value is not None:
                if isinstance(value, dict):
                    value = json.dumps(value)
                initial_value = value
            else:
                initial_value = ''
            field.initial = initial_value

    def save(self, category="default"):
        if not self.is_bound:
            raise ValueError("Form is not bound")

        # db_settings = Setting.objects.all()
        if not self.is_valid():
            raise ValueError(self.errors)

        with transaction.atomic():
            for name, value in self.cleaned_data.items():
                field = self.fields[name]
                if isinstance(field.widget, forms.PasswordInput) and not value:
                    continue
                if value == getattr(settings, name):
                    continue

                encrypted = True if isinstance(field, FormEncryptMixin) else False
                try:
                    setting = Setting.objects.get(name=name)
                except Setting.DoesNotExist:
                    setting = Setting()
                setting.name = name
                setting.category = category
                setting.encrypted = encrypted
                setting.cleaned_value = value
                setting.save()


class BasicSettingForm(BaseForm):
    SITE_URL = forms.URLField(
        label=_("Current SITE URL"),
        help_text="eg: http://jumpserver.abc.com:8080"
    )
    USER_GUIDE_URL = forms.URLField(
        label=_("User Guide URL"), required=False,
        help_text=_("User first login update profile done redirect to it")
    )
    EMAIL_SUBJECT_PREFIX = forms.CharField(
        max_length=1024, label=_("Email Subject Prefix"),
        help_text=_("Tips: Some word will be intercept by mail provider")
    )


class EmailSettingForm(BaseForm):
    EMAIL_HOST = forms.CharField(
        max_length=1024, label=_("SMTP host"), initial='smtp.jumpserver.org'
    )
    EMAIL_PORT = forms.CharField(max_length=5, label=_("SMTP port"), initial=25)
    EMAIL_HOST_USER = forms.CharField(
        max_length=128, label=_("SMTP user"), initial='noreply@jumpserver.org'
    )
    EMAIL_HOST_PASSWORD = FormEncryptCharField(
        max_length=1024, label=_("SMTP password"), widget=forms.PasswordInput,
        required=False,
        help_text=_("Tips: Some provider use token except password")
    )
    EMAIL_FROM = forms.CharField(
        max_length=128, label=_("Send user"), initial='', required=False,
        help_text=_(
            "Tips: Send mail account, default SMTP account as the send account"
        )
    )
    EMAIL_USE_SSL = forms.BooleanField(
        label=_("Use SSL"), initial=False, required=False,
        help_text=_("If SMTP port is 465, may be select")
    )
    EMAIL_USE_TLS = forms.BooleanField(
        label=_("Use TLS"), initial=False, required=False,
        help_text=_("If SMTP port is 587, may be select")
    )


class LDAPSettingForm(BaseForm):
    AUTH_LDAP_SERVER_URI = forms.CharField(
        label=_("LDAP server"),
    )
    AUTH_LDAP_BIND_DN = forms.CharField(
        required=False, label=_("Bind DN"),
    )
    AUTH_LDAP_BIND_PASSWORD = FormEncryptCharField(
        label=_("Password"),
        widget=forms.PasswordInput, required=False
    )
    AUTH_LDAP_SEARCH_OU = forms.CharField(
        label=_("User OU"),
        help_text=_("Use | split User OUs"),
        required=False,
    )
    AUTH_LDAP_SEARCH_FILTER = forms.CharField(
        label=_("User search filter"),
        help_text=_("Choice may be (cn|uid|sAMAccountName)=%(user)s)")
    )
    AUTH_LDAP_USER_ATTR_MAP = FormDictField(
        label=_("User attr map"),
        help_text=_(
            "User attr map present how to map LDAP user attr to jumpserver, "
            "username,name,email is jumpserver attr"
        ),
    )
    # AUTH_LDAP_GROUP_SEARCH_OU = CONFIG.AUTH_LDAP_GROUP_SEARCH_OU
    # AUTH_LDAP_GROUP_SEARCH_FILTER = CONFIG.AUTH_LDAP_GROUP_SEARCH_FILTER
    # AUTH_LDAP_START_TLS = forms.BooleanField(
    #     label=_("Use SSL"), required=False
    # )
    AUTH_LDAP = forms.BooleanField(label=_("Enable LDAP auth"), required=False)


class TerminalSettingForm(BaseForm):
    SORT_BY_CHOICES = (
        ('hostname', _('Hostname')),
        ('ip', _('IP')),
    )
    PAGE_SIZE_CHOICES = (
        ('all', _('All')),
        ('auto', _('Auto')),
        (10, 10),
        (15, 15),
        (25, 25),
        (50, 50),
    )
    TERMINAL_PASSWORD_AUTH = forms.BooleanField(
        required=False, label=_("Password auth")
    )
    TERMINAL_PUBLIC_KEY_AUTH = forms.BooleanField(
        required=False, label=_("Public key auth")
    )
    TERMINAL_HEARTBEAT_INTERVAL = forms.IntegerField(
        min_value=5, max_value=99999, label=_("Heartbeat interval"),
        help_text=_("Units: seconds")
    )
    TERMINAL_ASSET_LIST_SORT_BY = forms.ChoiceField(
        choices=SORT_BY_CHOICES, label=_("List sort by")
    )
    TERMINAL_ASSET_LIST_PAGE_SIZE = forms.ChoiceField(
        choices=PAGE_SIZE_CHOICES, label=_("List page size"),
    )
    TERMINAL_SESSION_KEEP_DURATION = forms.IntegerField(
        min_value=1, max_value=99999, label=_("Session keep duration"),
        help_text=_("Units: days, Session, record, command will be delete "
                    "if more than duration, only in database")
    )
    TERMINAL_TELNET_REGEX = forms.CharField(
        required=False, label=_("Telnet login regex"),
        help_text=_("ex: Last\s*login|success|成功")
    )


class TerminalCommandStorage(BaseForm):
    pass


class SecuritySettingForm(BaseForm):
    # MFA global setting
    SECURITY_MFA_AUTH = forms.BooleanField(
        required=False, label=_("MFA Secondary certification"),
        help_text=_(
            'After opening, the user login must use MFA secondary '
            'authentication (valid for all users, including administrators)'
        )
    )
    # Execute commands for user
    SECURITY_COMMAND_EXECUTION = forms.BooleanField(
        required=False, label=_("Batch execute commands"),
        help_text=_("Allow user batch execute commands")
    )
    # limit login count
    SECURITY_LOGIN_LIMIT_COUNT = forms.IntegerField(
        min_value=3, max_value=99999,
        label=_("Limit the number of login failures")
    )
    # limit login time
    SECURITY_LOGIN_LIMIT_TIME = forms.IntegerField(
        min_value=5, max_value=99999, label=_("No logon interval"),
        help_text=_(
            "Tip: (unit/minute) if the user has failed to log in for a limited "
            "number of times, no login is allowed during this time interval."
        )
    )
    # ssh max idle time
    SECURITY_MAX_IDLE_TIME = forms.IntegerField(
        min_value=1, max_value=99999, required=False,
        label=_("Connection max idle time"),
        help_text=_(
            'If idle time more than it, disconnect connection(only ssh now) '
            'Unit: minute'
        ),
    )
    # password expiration time
    SECURITY_PASSWORD_EXPIRATION_TIME = forms.IntegerField(
        min_value=1, max_value=99999, label=_("Password expiration time"),
        help_text=_(
            "Tip: (unit: day) "
            "If the user does not update the password during the time, "
            "the user password will expire failure;"
            "The password expiration reminder mail will be automatic sent to the user "
            "by system within 5 days (daily) before the password expires"
        )
    )
    # min length
    SECURITY_PASSWORD_MIN_LENGTH = forms.IntegerField(
        min_value=6, max_value=30, label=_("Password minimum length"),
    )
    # upper case
    SECURITY_PASSWORD_UPPER_CASE = forms.BooleanField(
        required=False, label=_("Must contain capital letters"),
        help_text=_(
            'After opening, the user password changes '
            'and resets must contain uppercase letters')
    )
    # lower case
    SECURITY_PASSWORD_LOWER_CASE = forms.BooleanField(
        required=False, label=_("Must contain lowercase letters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain lowercase letters')
    )
    # number
    SECURITY_PASSWORD_NUMBER = forms.BooleanField(
        required=False, label=_("Must contain numeric characters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain numeric characters')
    )
    # special char
    SECURITY_PASSWORD_SPECIAL_CHAR = forms.BooleanField(
        required=False, label=_("Must contain special characters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain special characters')
    )


class EmailContentSettingForm(BaseForm):
    EMAIL_CUSTOM_USER_CREATED_SUBJECT = forms.CharField(
        max_length=1024,  required=False, label=_("Create user email subject"),
        help_text=_("Tips: When creating a user, send the subject of the email"
                    " (eg:Create account successfully)")
    )
    EMAIL_CUSTOM_USER_CREATED_HONORIFIC = forms.CharField(
        max_length=1024, required=False, label=_("Create user honorific"),
        help_text=_("Tips: When creating a user, send the honorific of the "
                    "email (eg:Hello)")
    )
    EMAIL_CUSTOM_USER_CREATED_BODY = forms.CharField(
        max_length=4096, required=False, widget=forms.Textarea(),
        label=_('Create user email content'),
        help_text=_('Tips:When creating a user, send the content of the email')
    )
    EMAIL_CUSTOM_USER_CREATED_SIGNATURE = forms.CharField(
        max_length=512, required=False, label=_("Signature"),
        help_text=_("Tips: Email signature (eg:jumpserver)")
    )


