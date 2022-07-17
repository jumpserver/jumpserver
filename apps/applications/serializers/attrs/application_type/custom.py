from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import EncryptedField
from ..application_category import RemoteAppSerializer

__all__ = ['CustomSerializer', 'CustomSecretSerializer']


class CustomSerializer(RemoteAppSerializer):
    custom_cmdline = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Operating parameter'),
        allow_null=True,
    )
    custom_target = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Target url'),
        allow_null=True,
    )
    custom_username = serializers.CharField(
        max_length=128, allow_blank=True, required=False, label=_('Custom Username'),
        allow_null=True,
    )
    custom_password = EncryptedField(
        max_length=128, allow_blank=True, required=False,
        label=_('Custom password'), allow_null=True,
    )


class CustomSecretSerializer(RemoteAppSerializer):
    custom_password = EncryptedField(
        max_length=128, allow_blank=True, required=False, write_only=False,
        label=_('Custom password'), allow_null=True,
    )
