# coding: utf-8
#

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = [
    'RadiusSettingSerializer',
]


class RadiusSettingSerializer(serializers.Serializer):
    AUTH_RADIUS = serializers.BooleanField(required=False, label=_('Enable RADIUS Auth'))
    RADIUS_SERVER = serializers.CharField(required=False, max_length=1024, label=_('Host'))
    RADIUS_PORT = serializers.IntegerField(required=False, label=_('Port'))
    RADIUS_SECRET = serializers.CharField(
        required=False, max_length=1024, allow_null=True, label=_('Secret'), write_only=True
    )
    RADIUS_ENCRYPT_PASSWORD = serializers.BooleanField(required=False, label=_('Encrypt password'))
    OTP_IN_RADIUS = serializers.BooleanField(required=False, label=_('Otp in radius'))
