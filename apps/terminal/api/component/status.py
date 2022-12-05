# -*- coding: utf-8 -*-
#

import datetime
import logging
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import Response
from rest_framework import status

from terminal.models import Terminal, Status, Session
from terminal import serializers
from terminal.utils import TypedComponentsStatusMetricsUtil

logger = logging.getLogger(__file__)


__all__ = ['StatusViewSet', 'ComponentsMetricsAPIView']


class StatusViewSet(viewsets.ModelViewSet):
    queryset = Status.objects.all()
    serializer_class = serializers.StatSerializer
    session_serializer_class = serializers.SessionSerializer
    task_serializer_class = serializers.TaskSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.handle_sessions()
        self.perform_create(serializer)
        task_serializer = self.get_task_serializer()
        return Response(task_serializer.data, status=201)

    def handle_sessions(self):
        session_ids = self.request.data.get('sessions', [])
        Session.set_sessions_active(session_ids)

    def perform_create(self, serializer):
        serializer.validated_data.pop('sessions', None)
        serializer.validated_data["terminal"] = self.request.user.terminal
        return super().perform_create(serializer)

    def get_task_serializer(self):
        critical_time = timezone.now() - datetime.timedelta(minutes=10)
        tasks = self.request.user.terminal.task_set.filter(is_finished=False, date_created__gte=critical_time)
        serializer = self.task_serializer_class(tasks, many=True)
        return serializer

    def get_queryset(self):
        terminal_id = self.kwargs.get("terminal", None)
        if terminal_id:
            terminal = get_object_or_404(Terminal, id=terminal_id)
            return terminal.status_set.all()
        return super().get_queryset()


class ComponentsMetricsAPIView(generics.GenericAPIView):
    """ 返回汇总组件指标数据 """
    rbac_perms = {
        'GET': 'terminal.view_terminal'
    }

    def get(self, request, *args, **kwargs):
        util = TypedComponentsStatusMetricsUtil()
        metrics = util.get_metrics()
        return Response(metrics, status=status.HTTP_200_OK)
