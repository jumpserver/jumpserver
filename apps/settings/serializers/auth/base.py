from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

__all__ = [
    'AuthSettingSerializer',
]


class AuthSettingSerializer(serializers.Serializer):
    AUTH_CAS = serializers.BooleanField(required=False, label=_('CAS Auth'))
    AUTH_OPENID = serializers.BooleanField(required=False, label=_('OPENID Auth'))
    AUTH_RADIUS = serializers.BooleanField(required=False, label=_('RADIUS Auth'))
