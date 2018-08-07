# ~*~ coding: utf-8 ~*~
import uuid
import os

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import viewsets, generics
from rest_framework.views import Response

from common.const import tee_cache_key_fmt
from common.permissions import IsOrgAdmin
from .hands import IsSuperUser
from .models import Task, AdHoc, AdHocRunHistory, CeleryTask
from .serializers import TaskSerializer, AdHocSerializer, \
    AdHocRunHistorySerializer
from .tasks import run_ansible_task
from .celery import app


class TaskViewSet(viewsets.ModelViewSet):
    queryset = Task.objects.all()
    serializer_class = TaskSerializer
    permission_classes = (IsOrgAdmin,)
    label = None
    help_text = ''


class TaskRun(generics.RetrieveAPIView):
    queryset = Task.objects.all()
    serializer_class = TaskViewSet
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        task = self.get_object()
        t = run_ansible_task.delay(str(task.id))
        return Response({"task": t.id})


class AdHocViewSet(viewsets.ModelViewSet):
    queryset = AdHoc.objects.all()
    serializer_class = AdHocSerializer
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        task_id = self.request.query_params.get('task')
        if task_id:
            task = get_object_or_404(Task, id=task_id)
            self.queryset = self.queryset.filter(task=task)
        return self.queryset


class AdHocRunHistorySet(viewsets.ModelViewSet):
    queryset = AdHocRunHistory.objects.all()
    serializer_class = AdHocRunHistorySerializer
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


class CeleryTaskLogApi(generics.RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)
    buff_size = 1024 * 10
    end = False
    queryset = CeleryTask.objects.all()
    _redis = app.backend.client

    def get(self, request, *args, **kwargs):
        mark = request.query_params.get("mark") or str(uuid.uuid4())
        task = self.get_object()
        task_id = kwargs.get('pk')
        tee_cache_key = tee_cache_key_fmt.format(task_id)
        tee_cache_key_len = self._redis.strlen(tee_cache_key)

        if tee_cache_key_len == 0:
            return Response({"data": _("Waiting ...")}, status=203)

        offset = cache.get(mark, 0)
        diff_size = tee_cache_key_len - offset
        buff_size = self.buff_size if diff_size > self.buff_size else diff_size
        end_pos = offset + buff_size
        data = app.backend.client.getrange(
            tee_cache_key, offset, end_pos).replace(b'\n', b'\r\n')
        mark = str(uuid.uuid4())

        if data == b'':
            end_pos = offset
            if task.is_finished():
                self.end = True

        cache.set(mark, end_pos, 5)
        return Response({"data": data, 'end': self.end, 'mark': mark})

