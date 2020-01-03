# coding: utf-8
#

from django import forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseForm


__all__ = ['SecuritySettingForm']


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
    SECURITY_SERVICE_ACCOUNT_REGISTRATION = forms.BooleanField(
        required=False, label=_("Service account registration"),
        help_text=_("Allow using bootstrap token register service account, "
                    "when terminal setup, can disable it")
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
            'If idle time more than it, disconnect connection '
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
