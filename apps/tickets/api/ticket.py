# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from common.const.http import POST, PUT
from common.mixins.api import CommonApiMixin
from common.drf.api import JMSBulkModelViewSet

from rbac.permissions import RBACPermission

from tickets import serializers
from tickets.models import Ticket, TicketFlow
from tickets.filters import TicketFilter
from tickets.permissions.ticket import IsAssignee, IsApplicant

__all__ = ['TicketViewSet', 'TicketFlowViewSet']


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketDisplaySerializer
    serializer_classes = {
        'open': serializers.TicketApplySerializer,
        'approve': serializers.TicketApproveSerializer,
    }
    filterset_class = TicketFilter
    search_fields = [
        'title', 'action', 'type', 'status', 'applicant_display'
    ]
    ordering_fields = (
        'title', 'applicant_display', 'status', 'state', 'action_display',
        'date_created', 'serial_num',
    )
    ordering = ('-date_created',)
    rbac_perms = {
        'open': 'tickets.view_ticket',
    }

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def get_queryset(self):
        queryset = Ticket.get_user_related_tickets(self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.create_related_node()
        instance.process_map = instance.create_process_map()
        instance.open(applicant=self.request.user)

    @action(detail=False, methods=[POST], permission_classes=[RBACPermission, ])
    def open(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def approve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        instance.approve(processor=request.user)
        return Response(serializer.data)

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        instance.reject(processor=request.user)
        return Response(serializer.data)

    @action(detail=True, methods=[PUT], permission_classes=[IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        instance.close(processor=request.user)
        return Response(serializer.data)


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
