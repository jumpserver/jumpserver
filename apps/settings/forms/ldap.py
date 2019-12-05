# coding: utf-8
# 

from django import forms
from django.utils.translation import ugettext_lazy as _

from common.fields import FormDictField, FormEncryptCharField
from .base import BaseForm


__all__ = ['LDAPSettingForm']


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
