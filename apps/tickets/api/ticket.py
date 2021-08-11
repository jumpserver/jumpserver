# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from common.const.http import POST, PUT
from common.mixins.api import CommonApiMixin
from common.permissions import IsValidUser, IsOrgAdmin, IsSuperUser
from common.drf.api import JMSBulkModelViewSet

from tickets import serializers
from tickets.models import Ticket, TicketFlow
from tickets.permissions.ticket import IsAssignee, IsAssigneeOrApplicant, NotClosed

__all__ = ['TicketViewSet', 'TicketFlowViewSet']


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.TicketDisplaySerializer
    serializer_classes = {
        'open': serializers.TicketApplySerializer,
        'approve': serializers.TicketApproveSerializer,
    }
    filterset_fields = [
        'id', 'title', 'type', 'approve_level', 'status', 'applicant', 'assignees__id', 'applicant_display',
        'm2m_ticket_users__approve_level', 'm2m_ticket_users__is_processor', 'm2m_ticket_users__action'
    ]
    search_fields = [
        'title', 'action', 'type', 'status', 'applicant_display'
    ]

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
        instance.create_related_assignees()
        instance.process = instance.create_process_nodes()
        instance.open(applicant=self.request.user)

    @action(detail=False, methods=[POST], permission_classes=[IsValidUser, ])
    def open(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, NotClosed])
    def approve(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        instance = self.get_object()
        instance.approve(processor=self.request.user)
        return response

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, NotClosed])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        instance.reject(processor=request.user)
        return Response(serializer.data)

    @action(detail=True, methods=[PUT], permission_classes=[IsAssigneeOrApplicant, NotClosed])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        instance.close(processor=request.user)
        return Response(serializer.data)


class TicketFlowViewSet(JMSBulkModelViewSet):
    permission_classes = (IsOrgAdmin, IsSuperUser)
    serializer_class = serializers.TicketFlowSerializer

    filterset_fields = ['id', 'title', 'type']
    search_fields = ['id', 'title', 'type']

    def get_queryset(self):
        queryset = TicketFlow.get_org_related_flows()
        return queryset

    def perform_create_or_update(self, serializer):
        instance = serializer.save()
        instance.save()
        instance.ticket_flow_approves.model.change_assignees_display(instance.ticket_flow_approves.all())

    def perform_create(self, serializer):
        self.perform_create_or_update(serializer)

    def perform_update(self, serializer):
        self.perform_create_or_update(serializer)
