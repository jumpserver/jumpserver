# -*- coding: utf-8 -*-
#

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from common.const.http import POST, PUT
from common.mixins.api import CommonApiMixin
from common.permissions import IsValidUser, IsOrgAdmin

from tickets import serializers
from tickets.models import Ticket
from tickets.permissions.ticket import IsAssignee, IsAssigneeOrApplicant, NotClosed


__all__ = ['TicketViewSet']


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.TicketDisplaySerializer
    serializer_classes = {
        'open': serializers.TicketApplySerializer,
        'approve': serializers.TicketApproveSerializer,
    }
    filterset_fields = [
        'id', 'title', 'type', 'action', 'status', 'applicant', 'applicant_display', 'processor',
        'processor_display', 'assignees__id'
    ]
    search_fields = [
        'title', 'action', 'type', 'status', 'applicant_display', 'processor_display'
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
        instance.open(applicant=self.request.user)

    @action(detail=False, methods=[POST], permission_classes=[IsValidUser, ])
    def open(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PUT], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
    def approve(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)
        instance = self.get_object()
        instance.approve(processor=self.request.user)
        return response

    @action(detail=True, methods=[PUT], permission_classes=[IsOrgAdmin, IsAssignee, NotClosed])
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
