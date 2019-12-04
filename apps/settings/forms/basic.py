# coding: utf-8
#

from django import forms
from django.utils.translation import ugettext_lazy as _
from .base import BaseForm

__all__ = ['BasicSettingForm']


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

