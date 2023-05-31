# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.response import Response

from common.api import CommonApiMixin
from common.const.http import POST, PUT, PATCH
from orgs.utils import tmp_to_root_org
from rbac.permissions import RBACPermission
from tickets import filters
from tickets import serializers
from tickets.models import (
    Ticket, ApplyAssetTicket, ApplyLoginTicket,
    ApplyLoginAssetTicket, ApplyCommandTicket
)
from tickets.permissions.ticket import IsAssignee, IsApplicant

__all__ = [
    'TicketViewSet', 'ApplyAssetTicketViewSet',
    'ApplyLoginTicketViewSet', 'ApplyLoginAssetTicketViewSet',
    'ApplyCommandTicketViewSet'
]


class TicketViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketSerializer
    serializer_classes = {
        'approve': serializers.TicketApproveSerializer
    }
    model = Ticket
    perm_model = Ticket
    filterset_class = filters.TicketFilter
    search_fields = [
        'title', 'type', 'status'
    ]
    ordering = ('-date_created',)
    rbac_perms = {
        'open': 'tickets.view_ticket',
    }


    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        with tmp_to_root_org():
            serializer = self.get_serializer(instance)
            data = serializer.data
        return Response(data)

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

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee | IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.close()
        return Response('ok')


class ApplyAssetTicketViewSet(TicketViewSet):
    model = ApplyAssetTicket
    filterset_class = filters.ApplyAssetTicketFilter
    serializer_class = serializers.ApplyAssetSerializer
    serializer_classes = {
        'open': serializers.ApplyAssetSerializer,
        'approve': serializers.ApproveAssetSerializer
    }


class ApplyLoginTicketViewSet(TicketViewSet):
    model = ApplyLoginTicket
    filterset_class = filters.ApplyLoginTicketFilter
    serializer_class = serializers.LoginReviewSerializer


class ApplyLoginAssetTicketViewSet(TicketViewSet):
    model = ApplyLoginAssetTicket
    filterset_class = filters.ApplyLoginAssetTicketFilter
    serializer_class = serializers.LoginAssetReviewSerializer


class ApplyCommandTicketViewSet(TicketViewSet):
    model = ApplyCommandTicket
    filterset_class = filters.ApplyCommandTicketFilter
    serializer_class = serializers.ApplyCommandReviewSerializer
