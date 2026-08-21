from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from tickets import serializers
from tickets.models import TicketFlow
from common.api import JMSBulkModelViewSet
from common.const.http import GET

__all__ = ['TicketFlowViewSet']


class TicketFlowViewSet(JMSBulkModelViewSet):
    serializer_class = serializers.TicketFlowSerializer
    filterset_fields = ['id', 'name', 'type']
    search_fields = ['id', 'name', 'type']

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def get_queryset(self):
        queryset = TicketFlow.get_org_related_flows()
        return queryset

    @action(
        detail=False, methods=[GET], permission_classes=[IsAuthenticated],
        url_path='options'
    )
    def flow_options(self, request, *args, **kwargs):
        ticket_type = request.query_params.get('type')
        org_id = request.query_params.get('org_id')
        if not ticket_type or not org_id:
            return Response([])

        flows = TicketFlow.get_org_related_flows(org_id=org_id).filter(
            type=ticket_type
        ).prefetch_related('cc_users').order_by('name', 'date_created')
        serializer = serializers.TicketFlowOptionSerializer(flows, many=True)
        return Response(serializer.data)

    @action(
        detail=False, methods=[GET], permission_classes=[IsAuthenticated],
        url_path='cc-users'
    )
    def cc_users(self, request, *args, **kwargs):
        ticket_type = request.query_params.get('type')
        org_id = request.query_params.get('org_id')
        if not ticket_type or not org_id:
            return Response([])

        flow_id = request.query_params.get('flow_id')
        flows = TicketFlow.get_org_related_flows(org_id=org_id).filter(type=ticket_type)
        if flow_id:
            flows = flows.filter(id=flow_id)
        elif flows.count() != 1:
            return Response([])

        flow = flows.first()
        if not flow:
            return Response([])

        serializer = self.get_serializer(flow)
        return Response(serializer.data['cc_users'])

    def perform_create_or_update(self, serializer):
        instance = serializer.save()
        instance.save()

    def perform_create(self, serializer):
        self.perform_create_or_update(serializer)

    def perform_update(self, serializer):
        self.perform_create_or_update(serializer)
