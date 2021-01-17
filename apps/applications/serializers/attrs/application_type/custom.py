
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from ..application_category import RemoteAppSerializer


__all__ = ['CustomSerializer']


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
        max_length=128, allow_blank=True, required=False, label=_('Username'),
        allow_null=True,
    )
    custom_password = serializers.CharField(
        max_length=128, allow_blank=True, required=False, write_only=True, label=_('Password'),
        allow_null=True,
    )
