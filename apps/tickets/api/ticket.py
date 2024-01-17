# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from audits.handler import create_or_update_operate_log
from common.api import CommonApiMixin
from common.const.http import POST, PUT, PATCH
from orgs.utils import tmp_to_root_org, tmp_to_org
from rbac.permissions import RBACPermission
from tickets import filters
from tickets import serializers
from tickets.models import (
    Ticket, ApplyAssetTicket, ApplyLoginTicket,
    ApplyLoginAssetTicket, ApplyCommandTicket
)
from tickets.permissions.ticket import IsAssignee, IsApplicant
from ..const import TicketAction

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

    def ticket_not_allowed(self):
        if self.model == Ticket:
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

    @staticmethod
    def _record_operate_log(ticket, action):
        with tmp_to_org(ticket.org_id):
            after = {
                'ID': str(ticket.id),
                str(_('Name')): ticket.title,
                str(_('Applicant')): str(ticket.applicant),
            }
            object_name = ticket._meta.object_name
            resource_type = ticket._meta.verbose_name
            create_or_update_operate_log(
                action, resource_type, resource=ticket,
                after=after, object_name=object_name
            )

    @action(detail=True, methods=[PUT, PATCH], permission_classes=[IsAssignee, ])
    def approve(self, request, *args, **kwargs):
        self.ticket_not_allowed()

        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        with tmp_to_root_org():
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
        instance.approve(processor=request.user)
        self._record_operate_log(instance, TicketAction.approve)
        return Response('ok')

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def reject(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.reject(processor=request.user)
        self._record_operate_log(instance, TicketAction.reject)
        return Response('ok')

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee | IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.close()
        self._record_operate_log(instance, TicketAction.close)
        return Response('ok')

    @action(detail=False, methods=[PUT], permission_classes=[IsAuthenticated, ])
    def bulk(self, request, *args, **kwargs):
        self.ticket_not_allowed()

        allow_action = ('approve', 'reject')
        action_ = request.query_params.get('action')
        if action_ not in allow_action:
            msg = _("The parameter 'action' must be [{}]").format(','.join(allow_action))
            return Response({'error': msg}, status=400)

        ticket_ids = request.data.get('tickets', [])
        queryset = self.get_queryset().filter(state='pending').filter(id__in=ticket_ids)
        for obj in queryset:
            if not obj.has_current_assignee(request.user):
                return Response(
                    {'error': f"{_('User does not have permission')}: {obj}"}, status=400
                )
            handler = getattr(obj, action_)
            handler(processor=request.user)
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
