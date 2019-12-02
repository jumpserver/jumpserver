# coding: utf-8
#

from django import forms
from django.utils.translation import ugettext_lazy as _

from common.fields import FormEncryptCharField
from .base import BaseForm

__all__ = ['EmailSettingForm', 'EmailContentSettingForm']


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
    EMAIL_RECIPIENT = forms.CharField(
        max_length=128, label=_("Test recipient"), initial='', required=False,
        help_text=_("Tips: Used only as a test mail recipient")
    )
    EMAIL_USE_SSL = forms.BooleanField(
        label=_("Use SSL"), initial=False, required=False,
        help_text=_("If SMTP port is 465, may be select")
    )
    EMAIL_USE_TLS = forms.BooleanField(
        label=_("Use TLS"), initial=False, required=False,
        help_text=_("If SMTP port is 587, may be select")
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
