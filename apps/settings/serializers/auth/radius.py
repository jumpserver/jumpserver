# coding: utf-8
#

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from .base import OrgListField

__all__ = ['RadiusSettingSerializer']


class RadiusSettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('Radius')

    AUTH_RADIUS = serializers.BooleanField(required=False, label=_('Radius'))
    RADIUS_SERVER = serializers.CharField(required=False, allow_blank=True, max_length=1024, label=_('Host'))
    RADIUS_PORT = serializers.IntegerField(required=False, label=_('Port'))
    RADIUS_SECRET = EncryptedField(
        required=False, max_length=1024, allow_null=True, label=_('Secret'),
    )
    OTP_IN_RADIUS = serializers.BooleanField(
        required=False, label=_('OTP in RADIUS'),
        help_text=_('* Using OTP in RADIUS means users can employ RADIUS as a method for MFA')
    )
    RADIUS_ORG_IDS = OrgListField()
