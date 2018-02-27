# -*- coding: utf-8 -*-
#
import json

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape
from django.db import transaction
from django.conf import settings

from .models import Setting
from .fields import DictField


def to_model_value(value):
    try:
        return json.dumps(value)
    except json.JSONDecodeError:
        return None


def to_form_value(value):
    try:
        data = json.loads(value)
        if isinstance(data, dict):
            data = value
        return data
    except json.JSONDecodeError:
        return ""


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        db_settings = Setting.objects.all()
        for name, field in self.fields.items():
            db_value = getattr(db_settings, name).value
            django_value = getattr(settings, name) if hasattr(settings, name) else None
            if db_value is False or db_value:
                field.initial = to_form_value(db_value)
            elif django_value is False or django_value:
                field.initial = to_form_value(to_model_value(django_value))

    def save(self, category="default"):
        if not self.is_bound:
            raise ValueError("Form is not bound")

        db_settings = Setting.objects.all()
        if self.is_valid():
            with transaction.atomic():
                for name, value in self.cleaned_data.items():
                    field = self.fields[name]
                    if isinstance(field.widget, forms.PasswordInput) and not value:
                        continue
                    if value == to_form_value(getattr(db_settings, name).value):
                        continue

                    defaults = {
                        'name': name,
                        'category': category,
                        'value': to_model_value(value)
                    }
                    Setting.objects.update_or_create(defaults=defaults, name=name)
        else:
            raise ValueError(self.errors)


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
    EMAIL_HOST_PASSWORD = forms.CharField(
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
    AUTH_LDAP_BIND_PASSWORD = forms.CharField(
        label=_("Password"), initial='',
        widget=forms.PasswordInput, required=False
    )
    AUTH_LDAP_SEARCH_OU = forms.CharField(
        label=_("User OU"), initial='ou=tech,dc=jumpserver,dc=org'
    )
    AUTH_LDAP_SEARCH_FILTER = forms.CharField(
        label=_("User search filter"), initial='(cn=%(user)s)',
        help_text=_("User search filter must contain ([cn,uid,sAMAccountName,...]=%(user)s)")
    )
    AUTH_LDAP_USER_ATTR_MAP = DictField(
        label=_("User attr map"),
        initial=json.dumps({
            "username": "cn",
            "name": "sn",
            "email": "mail"
        }),
        help_text=_(
            "User attr map present how to map LDAP user attr to jumpserver, username,name,email is jumpserver attr")
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
    TERMINAL_COMMAND_STORAGE = DictField(
        label=_("Command storage"), help_text=_(
            "Set terminal storage setting, `default` is the using as default,"
            "You can set other storage and some terminal using"
        )
    )
    TERMINAL_REPLAY_STORAGE = DictField(
        label=_("Replay storage"), help_text=_(
            "Set replay storage setting, `default` is the using as default,"
            "You can set other storage and some terminal using"
        )
    )

