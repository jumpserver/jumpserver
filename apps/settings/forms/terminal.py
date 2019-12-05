# coding: utf-8
# 


from django import forms
from django.utils.translation import ugettext_lazy as _

from .base import BaseForm

__all__ = ['TerminalSettingForm']


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
