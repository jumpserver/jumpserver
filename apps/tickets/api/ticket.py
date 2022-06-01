# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed

from common.const.http import POST, PUT
from common.mixins.api import CommonApiMixin

from rbac.permissions import RBACPermission

from tickets import serializers
from tickets import filters
from tickets.permissions.ticket import IsAssignee, IsApplicant
from tickets.models import (
    Ticket, ApplyAssetTicket, ApplyApplicationTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)

__all__ = ['TicketViewSet', 'ApplyAssetTicketViewSet']


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketDisplaySerializer
    serializer_classes = {
        'open': serializers.TicketApplySerializer
    }
    filterset_class = filters.TicketFilter
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
    model = Ticket

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def get_queryset(self):
        queryset = self.model.get_user_related_tickets(self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        applicant = self.request.user
        instance.open(applicant)

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


class ApplyAssetTicketViewSet(TicketViewSet):
    serializer_class = serializers.ApplyAssetDisplaySerializer
    serializer_classes = {
        'open': serializers.ApplyAssetSerializer
    }
    model = ApplyAssetTicket
    filterset_class = filters.ApplyAssetTicketFilter


class ApplyApplicationTicketViewSet(TicketViewSet):
    serializer_class = serializers.ApplyApplicationDisplaySerializer
    serializer_classes = {
        'open': serializers.ApplyApplicationSerializer
    }
    model = ApplyApplicationTicket
    filterset_class = filters.ApplyApplicationTicketFilter
