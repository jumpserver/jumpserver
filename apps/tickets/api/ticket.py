# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed

from common.const.http import POST, PUT, PATCH
from common.mixins.api import CommonApiMixin
from orgs.utils import tmp_to_root_org

from rbac.permissions import RBACPermission

from tickets import serializers
from tickets import filters
from tickets.permissions.ticket import IsAssignee, IsApplicant
from tickets.models import (
    Ticket, ApplyAssetTicket, ApplyApplicationTicket,
    ApplyLoginTicket, ApplyLoginAssetTicket, ApplyCommandTicket
)

__all__ = [
    'TicketViewSet', 'ApplyAssetTicketViewSet', 'ApplyApplicationTicketViewSet',
    'ApplyLoginTicketViewSet', 'ApplyLoginAssetTicketViewSet', 'ApplyCommandTicketViewSet'
]


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketDisplaySerializer
    serializer_classes = {
        'list': serializers.TicketListSerializer,
        'open': serializers.TicketApplySerializer,
        'approve': serializers.TicketApproveSerializer
    }
    model = Ticket
    perm_model = Ticket
    filterset_class = filters.TicketFilter
    search_fields = [
        'title', 'type', 'status'
    ]
    ordering_fields = (
        'title', 'status', 'state',
        'action_display', 'date_created', 'serial_num',
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
        with tmp_to_root_org():
            queryset = self.model.get_user_related_tickets(self.request.user)
        return queryset

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.applicant = self.request.user
        instance.save(update_fields=['applicant'])
        instance.open()

    @action(detail=False, methods=[POST], permission_classes=[RBACPermission, ])
    def open(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().create(request, *args, **kwargs)

    @action(detail=True, methods=[PUT, PATCH], permission_classes=[IsAssignee, ])
    def approve(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        with tmp_to_root_org():
            serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.approve(processor=request.user)
        return Response('ok')

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.reject(processor=request.user)
        return Response('ok')

    @action(detail=True, methods=[PUT], permission_classes=[IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.close()
        return Response('ok')


class ApplyAssetTicketViewSet(TicketViewSet):
    serializer_class = serializers.ApplyAssetDisplaySerializer
    serializer_classes = {
        'open': serializers.ApplyAssetSerializer,
        'approve': serializers.ApproveAssetSerializer
    }
    model = ApplyAssetTicket
    filterset_class = filters.ApplyAssetTicketFilter


class ApplyApplicationTicketViewSet(TicketViewSet):
    serializer_class = serializers.ApplyApplicationDisplaySerializer
    serializer_classes = {
        'open': serializers.ApplyApplicationSerializer,
        'approve': serializers.ApproveApplicationSerializer
    }
    model = ApplyApplicationTicket
    filterset_class = filters.ApplyApplicationTicketFilter


class ApplyLoginTicketViewSet(TicketViewSet):
    serializer_class = serializers.LoginConfirmSerializer
    model = ApplyLoginTicket
    filterset_class = filters.ApplyLoginTicketFilter


class ApplyLoginAssetTicketViewSet(TicketViewSet):
    serializer_class = serializers.LoginAssetConfirmSerializer
    model = ApplyLoginAssetTicket
    filterset_class = filters.ApplyLoginAssetTicketFilter


class ApplyCommandTicketViewSet(TicketViewSet):
    serializer_class = serializers.ApplyCommandConfirmSerializer
    model = ApplyCommandTicket
    filterset_class = filters.ApplyCommandTicketFilter
