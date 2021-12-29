from rest_framework import serializers

from tickets.models import TicketSession


class TicketSessionRelationSerializer(serializers.ModelSerializer):

    class Meta:
        model = TicketSession
        fields = ['ticket', 'session']
