# -*- coding: utf-8 -*-
#
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer

from audits.handler import create_or_update_operate_log
from common.api import CommonApiMixin, ReportExportMixin
from common.const.http import POST, PUT, PATCH
from common.drf.throttling import FileTransferThrottle
from orgs.utils import tmp_to_root_org, tmp_to_org
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
        with tmp_to_root_org():
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            data = serializer.data
        return Response(data)

    @action(detail=True, methods=['get'], url_path='replay/download',
            permission_classes=[IsAuthenticated], throttle_classes=[FileTransferThrottle],
            renderer_classes=[JSONRenderer])
    def download_replay(self, request, *args, **kwargs):
        from terminal.api.session.session import SessionViewSet
        from terminal.models import Session
        from tickets.models import WorkflowEvent
        from tickets.plugins import get_ticket_plugin
        from tickets.workflow.approvers import user_snapshot

        plugin = get_ticket_plugin('download_replay')

        def authorize():
            with tmp_to_root_org():
                ticket = self.get_object()
            actions, status = plugin.get_replay_access(ticket, request.user)
            if not actions:
                raise PermissionDenied({'detail': _('No active approval for this session recording.'),
                                        'state': status['state']})
            return ticket, actions[0]

        ticket, access = authorize()

        def before_send():
            current_ticket, current_access = authorize()
            if current_access['session_id'] != access['session_id'] or current_ticket.org_id != ticket.org_id:
                raise PermissionDenied(_('The approved session recording changed.'))
            WorkflowEvent.objects.create(
                instance=current_ticket.workflow_instance, type='replay.downloaded', actor=request.user,
                actor_snapshot=user_snapshot(request.user),
                data={'session_id': access['session_id'], 'expires_at': current_access['expires_at']},
            )

        with tmp_to_org(ticket.org_id):
            session = get_object_or_404(Session, pk=access['session_id'], org_id=ticket.org_id, has_replay=True)
            try:
                return SessionViewSet.build_replay_download_response(session, request, before_send=before_send)
            except (OSError, ValueError) as exc:
                raise NotFound(_('The requested session recording is no longer available.')) from exc

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
        raise MethodNotAllowed(request.method, detail='Use the approval-task endpoint with an exact task ID.')

    @action(detail=True, methods=[PUT], permission_classes=[IsAssignee, ])
    def reject(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail='Use the approval-task endpoint with an exact task ID.')

    @action(detail=True, methods=[PUT], permission_classes=[IsApplicant, ])
    def close(self, request, *args, **kwargs):
        instance = self.get_object()
        with tmp_to_org(instance.org_id):
            instance.close(user=request.user)
        self._record_operate_log(instance, TicketAction.close)
        return Response('ok')

    @action(detail=False, methods=[PUT], permission_classes=[IsAuthenticated, ])
    def bulk(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method, detail='Use exact approval-task IDs.')
