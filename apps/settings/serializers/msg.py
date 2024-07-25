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
        smtp = 'smtp', _('SMTP')
        exchange = 'exchange', _('EXCHANGE')

    EMAIL_PROTOCOL = serializers.ChoiceField(
        choices=EmailProtocol.choices, label=_("Protocol"), default=EmailProtocol.smtp
    )
    EMAIL_HOST = serializers.CharField(max_length=1024, required=True, label=_("Host"))
    EMAIL_PORT = serializers.CharField(max_length=5, required=True, label=_("Port"))
    EMAIL_HOST_USER = serializers.CharField(
        max_length=128, required=False, allow_blank=True, label=_("Account"),
        help_text=_("The user to be used for email server authentication")
    )
    EMAIL_HOST_PASSWORD = EncryptedField(
        max_length=1024, required=False, label=_("Password"),
        help_text=_("Password to use for the email server. It is used in conjunction with `User` when authenticating to the email server")
    )
    EMAIL_FROM = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Sender'),
        help_text=_('Sender email address (default to using the `User`)')
    )
    EMAIL_RECIPIENT = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Recipient'),
        help_text=_("The recipient is used for testing the email server's connectivity")
    )
    EMAIL_USE_SSL = serializers.BooleanField(
        required=False, label=_('Use SSL'),
        help_text=_(
            'Whether to use an implicit TLS (secure) connection when talking to the SMTP server. In most email documentation this type of TLS connection is referred to as SSL. It is generally used on port 465')
    )
    EMAIL_USE_TLS = serializers.BooleanField(
        required=False, label=_("Use TLS"),
        help_text=_(
            'Whether to use a TLS (secure) connection when talking to the SMTP server. This is used for explicit TLS connections, generally on port 587')
    )


class EmailContentSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Email')

    EMAIL_SUBJECT_PREFIX = serializers.CharField(
        max_length=1024, required=True, label=_('Subject prefix')
    )
    EMAIL_CUSTOM_USER_CREATED_SUBJECT = serializers.CharField(
        max_length=1024, allow_blank=True, required=False,
        label=_('Subject'),
        help_text=_('Tips: When creating a user, send the subject of the email (eg:Create account successfully)')
    )
    EMAIL_CUSTOM_USER_CREATED_HONORIFIC = serializers.CharField(
        max_length=1024, allow_blank=True, required=False,
        label=_('Honorific'),
        help_text=_('Tips: When creating a user, send the honorific of the email (eg:Hello)')
    )
    EMAIL_CUSTOM_USER_CREATED_BODY = serializers.CharField(
        max_length=4096, allow_blank=True, required=False,
        label=_('Content'),
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
