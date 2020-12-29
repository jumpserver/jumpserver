
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from .mixin import BaseTicketMetaSerializer

__all__ = [
    'TicketMetaLoginConfirmApplySerializer',
]


class TicketMetaLoginConfirmSerializer(BaseTicketMetaSerializer):
    apply_login_ip = serializers.IPAddressField(
        required=True, allow_null=True, label=_('Login ip')
    )
    apply_login_city = serializers.CharField(
        required=True, allow_null=True, max_length=64, label=_('Login city')
    )
    apply_login_datetime = serializers.DateTimeField(
        required=True, allow_null=True, label=_('Login datetime')
    )


class TicketMetaLoginConfirmApplySerializer(BaseTicketMetaSerializer):
    pass
