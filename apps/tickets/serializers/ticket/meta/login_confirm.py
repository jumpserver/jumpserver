
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from common.fields.serializer import JSONFieldModelSerializer
from tickets.models import Ticket

__all__ = [
    'TicketMetaLoginConfirmSerializer', 'TicketMetaLoginConfirmApplySerializer',
]


class TicketMetaLoginConfirmSerializer(JSONFieldModelSerializer):
    apply_login_ip = serializers.IPAddressField(
        required=True, label=_('Login ip')
    )
    apply_login_city = serializers.CharField(
        required=True, max_length=64, label=_('Login city')
    )
    apply_login_datetime = serializers.DateTimeField(
        required=True, label=_('Login datetime')
    )

    class Meta:
        model = Ticket
        model_field = Ticket.meta
        fields = [
            'apply_login_ip', 'apply_login_city', 'apply_login_datetime'
        ]
        read_only_fields = fields


class TicketMetaLoginConfirmApplySerializer(TicketMetaLoginConfirmSerializer):

    class Meta(TicketMetaLoginConfirmSerializer.Meta):
        required_fields = [
            'apply_login_ip', 'apply_login_city', 'apply_login_datetime'
        ]
        read_only_fields = list(
            set(TicketMetaLoginConfirmSerializer.Meta.fields) - set(required_fields)
        )
