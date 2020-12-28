
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _


class TicketMetaLoginConfirmSerializer(serializers.Serializer):
    apply_login_ip = serializers.IPAddressField(
        allow_null=True, label=_('Login ip')
    )
    apply_login_city = serializers.CharField(
        allow_null=True, max_length=64, label=_('Login city')
    )
    apply_login_datetime = serializers.DateTimeField(
        allow_null=True, required=True, label=_('Login datetime')
    )
