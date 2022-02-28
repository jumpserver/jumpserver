from rest_framework.serializers import ModelSerializer

from ..models import SuperTicket


__all__ = ['SuperTicketSerializer']


class SuperTicketSerializer(ModelSerializer):
    class Meta:
        model = SuperTicket
        fields = ['id', 'status', 'state', 'processor']
