# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from rest_framework import viewsets, generics
from rest_framework.views import Response

from common.drf.api import JMSBulkModelViewSet
from common.permissions import IsOrgAdmin
from common.drf.serializers import CeleryTaskSerializer
from ..models import Task, AdHoc, AdHocExecution
from ..serializers import (
    TaskSerializer,
    AdHocSerializer,
    AdHocExecutionSerializer,
    TaskDetailSerializer,
    AdHocDetailSerializer,
)
from ..tasks import run_ansible_task

__all__ = [
    'TaskViewSet', 'TaskRun', 'AdHocViewSet', 'AdHocRunHistoryViewSet'
]


class TaskViewSet(JMSBulkModelViewSet):
    queryset = Task.objects.all()
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = TaskSerializer
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TaskDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.select_related('latest_execution')
        return queryset


class TaskRun(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = CeleryTaskSerializer
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        t = run_ansible_task.delay(str(task.id))
        return Response({"task": t.id})


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return AdHocDetailSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            self.queryset = self.queryset.filter(task=task)
        return self.queryset


class AdHocRunHistoryViewSet(viewsets.ModelViewSet):
    queryset = AdHocExecution.objects.all()
    serializer_class = AdHocExecutionSerializer
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        adhoc_id = self.request.query_params.get('adhoc')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            adhocs = task.adhoc.all()
            self.queryset = self.queryset.filter(adhoc__in=adhocs)

        if adhoc_id:
            adhoc = get_object_or_404(AdHoc, id=adhoc_id)
            self.queryset = self.queryset.filter(adhoc=adhoc)
        return self.queryset





