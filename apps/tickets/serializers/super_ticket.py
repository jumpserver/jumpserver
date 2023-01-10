from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from common.serializers.fields import LabeledChoiceField
from tickets.const import TicketStatus, TicketState

from ..models import SuperTicket


__all__ = ['SuperTicketSerializer']


class SuperTicketSerializer(serializers.ModelSerializer):
    status = LabeledChoiceField(choices=TicketStatus.choices, read_only=True, label=_('Status'))
    state = LabeledChoiceField(choices=TicketState.choices, read_only=True, label=_("State"))
    processor = serializers.SerializerMethodField(label=_("Processor"))

    class Meta:
        model = SuperTicket
        fields = ['id', 'status', 'state', 'processor']

    @staticmethod
    def get_processor(instance):
        return str(instance.processor) if instance.processor else ''
