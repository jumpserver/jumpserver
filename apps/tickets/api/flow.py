from rest_framework.exceptions import MethodNotAllowed

from tickets import serializers
from tickets.models import TicketFlow
from common.api import JMSBulkModelViewSet

__all__ = ['TicketFlowViewSet']


class TicketFlowViewSet(JMSBulkModelViewSet):
    serializer_class = serializers.TicketFlowSerializer
    filterset_fields = ['id', 'type']
    search_fields = ['id', 'type']

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def get_queryset(self):
        queryset = TicketFlow.get_org_related_flows()
        return queryset

    def perform_create_or_update(self, serializer):
        instance = serializer.save()
        instance.save()

    def perform_create(self, serializer):
        self.perform_create_or_update(serializer)

    def perform_update(self, serializer):
        self.perform_create_or_update(serializer)
