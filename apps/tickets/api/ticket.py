# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from audits.handler import create_or_update_operate_log
from common.api import CommonApiMixin, ReportExportMixin
from common.const.http import POST, PUT, PATCH
from orgs.utils import current_org, tmp_to_root_org, tmp_to_org
from rbac.permissions import RBACPermission
from tickets import filters
from tickets import serializers
from tickets.reporting import TicketReportExporter
from tickets.models import Ticket
from tickets.permissions.ticket import IsAssignee, IsApplicant
from tickets.errors import AlreadyClosed
from ..const import TicketAction

__all__ = ['TicketViewSet']


class TicketViewSet(ReportExportMixin, CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = serializers.TicketSerializer
    serializer_classes = {
        'approve': serializers.TicketApproveSerializer,
        'open': serializers.PluginTicketApplySerializer,
    }
    model = Ticket
    report_exporter_class = TicketReportExporter
    perm_model = Ticket
    filterset_class = filters.TicketFilter
    search_fields = [
        'title', 'type', 'status'
    ]
    ordering_fields = [
        'title', 'serial_num', 'type', 'state', 'status', 'origin', 'applicant',
        'date_created',
    ]
    ordering = ('-date_created',)
    rbac_perms = {
        'open': 'tickets.view_ticket',
        'retrieve': 'tickets.view_ticket | audits.view_ticketaudit',
    }

    def get_serializer_class(self):
        ticket_type = self.request.query_params.get('type')
        if (getattr(self, 'action', None) != 'open' and self.request.method in ('OPTIONS', 'POST')
                and ticket_type):
            from django.utils.module_loading import import_string
            from tickets.plugins import get_ticket_plugin
            plugin = get_ticket_plugin(ticket_type)
            if plugin.apply_serializer:
                return import_string(plugin.apply_serializer)
        return super().get_serializer_class()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        with tmp_to_org(instance.org_id):
            data = self.get_serializer(instance).data
        return Response(data)

    def get_plugin_action(self):
        from tickets.plugins import get_ticket_plugin
        from tickets.workflow.approvers import available_users
        if not hasattr(self, '_plugin_action'):
            with tmp_to_root_org():
                ticket = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
            if not current_org.is_root() and str(current_org.id) != str(ticket.org_id):
                raise NotFound()
            if not available_users(ticket.org_id).filter(pk=self.request.user.pk).exists():
                raise PermissionDenied()
            handler = get_ticket_plugin(ticket.type).get_action(self.kwargs['action_name'])
            if self.request.method not in (handler.method, 'OPTIONS'):
                raise MethodNotAllowed(self.request.method)
            self._action_ticket, self._plugin_action = ticket, handler
        return self._plugin_action

    def check_permissions(self, request):
        if self.action != 'perform_action' or not request.user.is_authenticated:
            return super().check_permissions(request)
        self.get_plugin_action()
        with tmp_to_org(self._action_ticket.org_id):
            return super().check_permissions(request)

    def get_permissions(self):
        permissions = super().get_permissions()
        if self.action == 'perform_action' and self.request.user.is_authenticated:
            permissions += [cls() for cls in self.get_plugin_action().permission_classes]
        return permissions

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.action == 'perform_action':
            throttles += [cls() for cls in self.get_plugin_action().throttle_classes]
        return throttles

    @action(detail=True, methods=['get', 'post'], url_path=r'actions/(?P<action_name>[a-z][a-z0-9_]*)',
            permission_classes=[IsAuthenticated], renderer_classes=[JSONRenderer])
    def perform_action(self, request, *args, **kwargs):
        handler = self.get_plugin_action()
        ticket = self._action_ticket
        with tmp_to_org(ticket.org_id):
            self.check_object_permissions(request, ticket)
            response = handler.execute(ticket, request)
        response['Cache-Control'] = 'no-store'
        response['Pragma'] = 'no-cache'
        return response

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def destroy(self, request, *args, **kwargs):
        raise MethodNotAllowed(self.action)

    def get_queryset(self):
        can_audit = self.action == 'retrieve' and self.request.user.has_perm('audits.view_ticketaudit')
        audit_org_id = None if current_org.is_root() else str(current_org.id)
        with tmp_to_root_org():
            queryset = self.model.get_user_related_tickets(self.request.user)
            if can_audit:
                if audit_org_id is None:
                    return self.model.objects.all()
                # Auditing one organization must not hide the user's own tickets elsewhere.
                return self.model.objects.filter(
                    Q(org_id=audit_org_id) | Q(pk__in=queryset.values('pk')),
                )
        return queryset

    @transaction.atomic
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
        raise MethodNotAllowed(request.method, detail=gettext('Use the approval-task endpoint with an exact task ID.'))

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def reject(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail=gettext('Use the approval-task endpoint with an exact task ID.'))

    @action(detail=True, methods=[PUT], permission_classes=[IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        with tmp_to_org(instance.org_id):
            instance.close(user=request.user)
        self._record_operate_log(instance, TicketAction.close)
        return Response('ok')

    @action(detail=False, methods=[PUT], permission_classes=[IsAuthenticated, ])
    def bulk(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail=gettext('Use exact approval-task IDs.'))
