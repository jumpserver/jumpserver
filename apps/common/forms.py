# -*- coding: utf-8 -*-
#
import json
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db import transaction
from django.conf import settings

from .models import Setting, common_settings
from .fields import FormDictField, FormEncryptCharField, \
    FormEncryptMixin, FormEncryptDictField


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            db_value = getattr(common_settings, name)
            django_value = getattr(settings, name) if hasattr(settings, name) else None

            if db_value is None and django_value is None:
                continue

            if db_value is False or db_value:
                if isinstance(db_value, dict):
                    db_value = json.dumps(db_value)
                initial_value = db_value
            elif django_value is False or django_value:
                initial_value = django_value
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
                if value == getattr(common_settings, name):
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
        initial="[Jumpserver] "
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
        required=False, help_text=_("Some provider use token except password")
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
        label=_("LDAP server"), initial='ldap://localhost:389'
    )
    AUTH_LDAP_BIND_DN = forms.CharField(
        label=_("Bind DN"), initial='cn=admin,dc=jumpserver,dc=org'
    )
    AUTH_LDAP_BIND_PASSWORD = FormEncryptCharField(
        label=_("Password"), initial='',
        widget=forms.PasswordInput, required=False
    )
    AUTH_LDAP_SEARCH_OU = forms.CharField(
        label=_("User OU"), initial='ou=tech,dc=jumpserver,dc=org',
        help_text=_("Use | split User OUs")
    )
    AUTH_LDAP_SEARCH_FILTER = forms.CharField(
        label=_("User search filter"), initial='(cn=%(user)s)',
        help_text=_("Choice may be (cn|uid|sAMAccountName)=%(user)s)")
    )
    AUTH_LDAP_USER_ATTR_MAP = FormDictField(
        label=_("User attr map"),
        help_text=_(
            "User attr map present how to map LDAP user attr to jumpserver, "
            "username,name,email is jumpserver attr"
        )
    )
    # AUTH_LDAP_GROUP_SEARCH_OU = CONFIG.AUTH_LDAP_GROUP_SEARCH_OU
    # AUTH_LDAP_GROUP_SEARCH_FILTER = CONFIG.AUTH_LDAP_GROUP_SEARCH_FILTER
    AUTH_LDAP_START_TLS = forms.BooleanField(
        label=_("Use SSL"), initial=False, required=False
    )
    AUTH_LDAP = forms.BooleanField(label=_("Enable LDAP auth"), initial=False, required=False)


class TerminalSettingForm(BaseForm):
    SORT_BY_CHOICES = (
        ('hostname', _('Hostname')),
        ('ip', _('IP')),
    )
    TERMINAL_ASSET_LIST_SORT_BY = forms.ChoiceField(
        choices=SORT_BY_CHOICES, initial='hostname', label=_("List sort by")
    )
    TERMINAL_HEARTBEAT_INTERVAL = forms.IntegerField(
        initial=5, label=_("Heartbeat interval"), help_text=_("Units: seconds")
    )
    TERMINAL_PASSWORD_AUTH = forms.BooleanField(
        initial=True, required=False, label=_("Password auth")
    )
    TERMINAL_PUBLIC_KEY_AUTH = forms.BooleanField(
        initial=True, required=False, label=_("Public key auth")
    )
    TERMINAL_COMMAND_STORAGE = FormEncryptDictField(
        label=_("Command storage"), help_text=_(
            "Set terminal storage setting, `default` is the using as default,"
            "You can set other storage and some terminal using"
        )
    )
    TERMINAL_REPLAY_STORAGE = FormEncryptDictField(
        label=_("Replay storage"), help_text=_(
            "Set replay storage setting, `default` is the using as default,"
            "You can set other storage and some terminal using"
        )
    )


class SecuritySettingForm(BaseForm):
    # MFA global setting
    SECURITY_MFA_AUTH = forms.BooleanField(
        initial=False, required=False,
        label=_("MFA Secondary certification"),
        help_text=_(
            'After opening, the user login must use MFA secondary '
            'authentication (valid for all users, including administrators)'
        )
    )
    # limit login count
    SECURITY_LOGIN_LIMIT_COUNT = forms.IntegerField(
        initial=7, min_value=3,
        label=_("Limit the number of login failures")
    )
    # limit login time
    SECURITY_LOGIN_LIMIT_TIME = forms.IntegerField(
        initial=30, min_value=5,
        label=_("No logon interval"),
        help_text=_(
            "Tip :(unit/minute) if the user has failed to log in for a limited "
            "number of times, no login is allowed during this time interval."
        )
    )
    SECURITY_MAX_IDLE_TIME = forms.IntegerField(
        initial=30, required=False,
        label=_("Connection max idle time"),
        help_text=_(
            'If idle time more than it, disconnect connection(only ssh now) '
            'Unit: minute'
        ),
    )
    # min length
    SECURITY_PASSWORD_MIN_LENGTH = forms.IntegerField(
        initial=6, label=_("Password minimum length"),
        min_value=6
    )
    # upper case
    SECURITY_PASSWORD_UPPER_CASE = forms.BooleanField(
        initial=False, required=False,
        label=_("Must contain capital letters"),
        help_text=_(
            'After opening, the user password changes '
            'and resets must contain uppercase letters')
    )
    # lower case
    SECURITY_PASSWORD_LOWER_CASE = forms.BooleanField(
        initial=False, required=False,
        label=_("Must contain lowercase letters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain lowercase letters')
    )
    # number
    SECURITY_PASSWORD_NUMBER = forms.BooleanField(
        initial=False, required=False,
        label=_("Must contain numeric characters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain numeric characters')
    )
    # special char
    SECURITY_PASSWORD_SPECIAL_CHAR = forms.BooleanField(
        initial=False, required=False,
        label=_("Must contain special characters"),
        help_text=_('After opening, the user password changes '
                    'and resets must contain special characters')
    )

