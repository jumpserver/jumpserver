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
    RADIUS_PUSH_ENABLED = serializers.BooleanField(
        required=False, label=_('RADIUS Push'),
        help_text=_('For web login, also allow RADIUS Push in the system MFA policy.'),
    )
    RADIUS_PUSH_TRIGGER = serializers.CharField(
        required=False, allow_blank=True, trim_whitespace=False, max_length=128,
        label=_('Push trigger'),
        help_text=_('The value your RADIUS provider expects to trigger a push. Leave blank for an empty password.'),
    )
    RADIUS_PUSH_TIMEOUT = serializers.IntegerField(
        required=False, min_value=5, max_value=120, label=_('Push timeout (seconds)'),
    )
    RADIUS_ORG_IDS = OrgListField()

    def validate_RADIUS_PUSH_TRIGGER(self, value):
        if len(value.encode('utf-8')) > 128:
            raise serializers.ValidationError(_('The RADIUS push trigger must be at most 128 bytes.'))
        return value
