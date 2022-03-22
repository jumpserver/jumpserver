from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from ..models import SuperTicket


__all__ = ['SuperTicketSerializer']


class SuperTicketSerializer(serializers.ModelSerializer):
    processor = serializers.SerializerMethodField(label=_("Processor"))

    class Meta:
        model = SuperTicket
        fields = ['id', 'status', 'state', 'processor']

    @staticmethod
    def get_processor(ticket):
        if not ticket.processor:
            return ''
        return str(ticket.processor)
