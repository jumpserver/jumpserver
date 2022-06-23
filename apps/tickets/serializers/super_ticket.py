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
    def get_processor(instance):
        if not instance.processor:
            return ''
        return str(instance.processor)
