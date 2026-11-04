from rest_framework import serializers

from terminal.models import Session
from tickets.models import TicketSession


class TicketSessionRelationSerializer(serializers.ModelSerializer):

    class Meta:
        model = TicketSession
        fields = ['ticket', 'session']


class TicketSessionSummarySerializer(serializers.ModelSerializer):
    terminal_type = serializers.CharField(source='terminal.type', default=None, read_only=True)

    class Meta:
        model = Session
        fields = ['id', 'org_id', 'asset', 'account', 'protocol', 'remote_addr', 'type', 'terminal_type',
                  'is_finished', 'is_locked', 'can_join', 'can_terminate']
