# -*- coding: utf-8 -*-
#
import logging
import uuid

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import APIView, Response
from rest_framework import status
from django.conf import settings


from common.drf.api import JMSBulkModelViewSet
from common.utils import get_object_or_none
from common.permissions import IsAppUser, IsOrgAdminOrAppUser, IsSuperUser, WithBootstrapToken
from ..models import Terminal, Status, Session
from .. import serializers
from .. import exceptions

__all__ = [
    'TerminalViewSet',  'StatusViewSet', 'TerminalConfig',
    'TerminalRegistrationApi',
]
logger = logging.getLogger(__file__)


class TerminalViewSet(JMSBulkModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    permission_classes = (IsSuperUser,)
    filterset_fields = ['name', 'remote_addr', 'type']

    def create(self, request, *args, **kwargs):
        if isinstance(request.data, list):
            raise exceptions.BulkCreateNotSupport()

        name = request.data.get('name')
        remote_ip = request.META.get('REMOTE_ADDR')
        x_real_ip = request.META.get('X-Real-IP')
        remote_addr = x_real_ip or remote_ip

        terminal = get_object_or_none(Terminal, name=name, is_deleted=False)
        if terminal:
            msg = 'Terminal name %s already used' % name
            return Response({'msg': msg}, status=409)

        serializer = self.serializer_class(data={
            'name': name, 'remote_addr': remote_addr
        })

        if serializer.is_valid():
            terminal = serializer.save()

            # App should use id, token get access key, if accepted
            token = uuid.uuid4().hex
            cache.set(token, str(terminal.id), 3600)
            data = {"id": str(terminal.id), "token": token, "msg": "Need accept"}
            return Response(data, status=201)
        else:
            data = serializer.errors
            logger.error("Register terminal error: {}".format(data))
            return Response(data, status=400)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        status = self.request.query_params.get('status')
        if not status:
            return queryset
        filtered_queryset_id = [str(q.id) for q in queryset if q.status == status]
        queryset = queryset.filter(id__in=filtered_queryset_id)
        return queryset


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = serializers.StatusSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    session_serializer_class = serializers.SessionSerializer
    task_serializer_class = serializers.TaskSerializer

    def create(self, request, *args, **kwargs):
        self.handle_sessions()
        tasks = self.request.user.terminal.task_set.filter(is_finished=False)
        serializer = self.task_serializer_class(tasks, many=True)
        return Response(serializer.data, status=201)

    def handle_sessions(self):
        sessions_id = self.request.data.get('sessions', [])
        # guacamole 上报的 session 是字符串
        # "[53cd3e47-210f-41d8-b3c6-a184f3, 53cd3e47-210f-41d8-b3c6-a184f4]"
        if isinstance(sessions_id, str):
            sessions_id = sessions_id[1:-1].split(',')
            sessions_id = [sid.strip() for sid in sessions_id if sid.strip()]
        Session.set_sessions_active(sessions_id)

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            self.queryset = terminal.status_set.all()
        return self.queryset

    def perform_create(self, serializer):
        serializer.validated_data["terminal"] = self.request.user.terminal
        return super().perform_create(serializer)

    def get_permissions(self):
        if self.action == "create":
            self.permission_classes = (IsAppUser,)
        return super().get_permissions()


class TerminalConfig(APIView):
    permission_classes = (IsAppUser,)

    def get(self, request):
        config = request.user.terminal.config
        return Response(config, status=200)


class TerminalRegistrationApi(generics.CreateAPIView):
    serializer_class = serializers.TerminalRegistrationSerializer
    permission_classes = [WithBootstrapToken]
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        if not settings.SECURITY_SERVICE_ACCOUNT_REGISTRATION:
            data = {"error": "service account registration disabled"}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)
