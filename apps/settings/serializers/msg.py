# coding: utf-8
#
from django.db import models
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField


__all__ = [
    'MailTestSerializer', 'EmailSettingSerializer',
    'EmailContentSettingSerializer', 'SMSBackendSerializer',
]


class MailTestSerializer(serializers.Serializer):
    EMAIL_FROM = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    EMAIL_RECIPIENT = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class EmailSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Email')

    class EmailProtocol(models.TextChoices):
        smtp = 'smtp',  _('SMTP')
        exchange = 'exchange', _('EXCHANGE')

    EMAIL_PROTOCOL = serializers.ChoiceField(
        choices=EmailProtocol.choices, label=_("Protocol"), default=EmailProtocol.smtp
    )
    EMAIL_HOST = serializers.CharField(max_length=1024, required=True, label=_("Host"))
    EMAIL_PORT = serializers.CharField(max_length=5, required=True, label=_("Port"))
    EMAIL_HOST_USER = serializers.CharField(max_length=128, required=True, label=_("Account"))
    EMAIL_HOST_PASSWORD = EncryptedField(
        max_length=1024, required=False, label=_("Password"),
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
        required=False, label=_('Use SSL'),
        help_text=_('If SMTP port is 465, may be select')
    )
    EMAIL_USE_TLS = serializers.BooleanField(
        required=False, label=_("Use TLS"),
        help_text=_('If SMTP port is 587, may be select')
    )
    EMAIL_SUBJECT_PREFIX = serializers.CharField(
        max_length=1024, required=True, label=_('Subject prefix')
    )
    EMAIL_SUFFIX = serializers.CharField(
        required=False, max_length=1024, label=_("Email suffix"),
        help_text=_('This is used by default if no email is returned during SSO authentication')
    )


class EmailContentSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Email')

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
        help_text=_(
            'Tips: When creating a user, send the content of the email, support {username} {name} {email} label')
    )
    EMAIL_CUSTOM_USER_CREATED_SIGNATURE = serializers.CharField(
        max_length=512, allow_blank=True, required=False, label=_('Signature'),
        help_text=_('Tips: Email signature (eg:jumpserver)')
    )


class SMSBackendSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=256, required=True, label=_('Name'))
    label = serializers.CharField(max_length=256, required=True, label=_('Label'))
