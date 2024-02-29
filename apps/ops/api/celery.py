# -*- coding: utf-8 -*-
#
import os
import re
from collections import defaultdict

from celery.result import AsyncResult
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from django_celery_beat.models import PeriodicTask
from django_filters import rest_framework as drf_filters
from rest_framework import generics, viewsets, mixins, status
from rest_framework.response import Response

from common.api import LogTailApi, CommonApiMixin
from common.drf.filters import BaseFilterSet
from common.exceptions import JMSException
from common.permissions import IsValidUser
from common.utils.timezone import local_now
from ops.celery import app
from ..ansible.utils import get_ansible_task_log_path
from ..celery.utils import get_celery_task_log_path
from ..models import CeleryTaskExecution, CeleryTask
from ..serializers import CeleryResultSerializer, CeleryPeriodTaskSerializer
from ..serializers.celery import CeleryTaskSerializer, CeleryTaskExecutionSerializer

__all__ = [
    'CeleryTaskExecutionLogApi', 'CeleryResultApi', 'CeleryPeriodTaskViewSet',
    'AnsibleTaskLogApi', 'CeleryTaskViewSet', 'CeleryTaskExecutionViewSet'
]


class CeleryTaskExecutionLogApi(LogTailApi):
    permission_classes = (IsValidUser,)
    task = None
    task_id = ''
    pattern = re.compile(r'Task .* succeeded in \d+\.\d+s.*')

    def get(self, request, *args, **kwargs):
        self.task_id = str(kwargs.get('pk'))
        self.task = AsyncResult(self.task_id)
        return super().get(request, *args, **kwargs)

    def filter_line(self, line):
        if self.pattern.match(line):
            line = self.pattern.sub(line, '')
        return line

    def get_log_path(self):
        new_path = get_celery_task_log_path(self.task_id)
        if new_path and os.path.isfile(new_path):
            return new_path
        try:
            task = CeleryTaskExecution.objects.get(id=self.task_id)
        except CeleryTaskExecution.DoesNotExist:
            return None
        return task.full_log_path

    def is_file_finish_write(self):
        return self.task.ready()

    def get_no_file_message(self, request):
        if self.mark == 'undefined':
            return '.'
        else:
            return _('Waiting task start')


class AnsibleTaskLogApi(LogTailApi):
    permission_classes = (IsValidUser,)

    def get_log_path(self):
        new_path = get_ansible_task_log_path(self.kwargs.get('pk'))
        if new_path and os.path.isfile(new_path):
            return new_path

    def get_no_file_message(self, request):
        if self.mark == 'undefined':
            return '.'
        else:
            return _('Waiting task start')


class CeleryResultApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = CeleryResultSerializer

    def get_object(self):
        pk = self.kwargs.get('pk')
        return AsyncResult(str(pk))


class CeleryPeriodTaskViewSet(CommonApiMixin, viewsets.ModelViewSet):
    queryset = PeriodicTask.objects.all()
    serializer_class = CeleryPeriodTaskSerializer
    http_method_names = ('get', 'head', 'options', 'patch')

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(description='')
        return queryset


class CelerySummaryAPIView(generics.RetrieveAPIView):
    def get(self, request, *args, **kwargs):
        pass


class CeleryTaskFilterSet(BaseFilterSet):
    id = drf_filters.CharFilter(field_name='id', lookup_expr='exact')
    name = drf_filters.CharFilter(method='filter_name')

    @staticmethod
    def filter_name(queryset, name, value):
        _ids = []
        for task in queryset:
            comment = task.meta.get('comment')
            if not comment:
                continue
            if value not in comment:
                continue
            _ids.append(task.id)
        queryset = queryset.filter(id__in=_ids)
        return queryset

    class Meta:
        model = CeleryTask
        fields = ['id', 'name']


class CeleryTaskViewSet(
    CommonApiMixin, mixins.RetrieveModelMixin,
    mixins.ListModelMixin, mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    search_fields = ('id', 'name')
    filterset_class = CeleryTaskFilterSet
    serializer_class = CeleryTaskSerializer

    def get_queryset(self):
        return CeleryTask.objects.exclude(name__startswith='celery')

    @staticmethod
    def extract_schedule(input_string):
        pattern = r'(\S+ \S+ \S+ \S+ \S+).*'
        match = re.match(pattern, input_string)
        if match:
            return match.group(1)
        else:
            return input_string

    def generate_execute_time(self, queryset):
        names = [i.name for i in queryset]
        periodic_tasks = PeriodicTask.objects.filter(name__in=names)
        periodic_task_dict = {task.name: task for task in periodic_tasks}
        now = local_now()
        for i in queryset:
            task = periodic_task_dict.get(i.name)
            if not task:
                continue
            i.exec_cycle = self.extract_schedule(str(task.scheduler))

            last_run_at = task.last_run_at or now
            next_run_at = task.schedule.remaining_estimate(last_run_at)
            if next_run_at.total_seconds() < 0:
                next_run_at = task.schedule.remaining_estimate(now)
            i.next_exec_time = now + next_run_at
        return queryset

    def generate_summary_state(self, execution_qs):
        model = self.get_queryset().model
        executions = execution_qs.order_by('-date_published').values('name', 'state')
        summary_state_dict = defaultdict(
            lambda: {
                'states': [], 'state': 'green',
                'summary': {'total': 0, 'success': 0}
            }
        )
        for execution in executions:
            name = execution['name']
            state = execution['state']

            summary = summary_state_dict[name]['summary']

            summary['total'] += 1
            summary['success'] += 1 if state == 'SUCCESS' else 0

            states = summary_state_dict[name].get('states')
            if states is not None and len(states) >= 5:
                color = model.compute_state_color(states)
                summary_state_dict[name]['state'] = color
                summary_state_dict[name].pop('states', None)
            elif isinstance(states, list):
                states.append(state)

        return summary_state_dict

    def loading_summary_state(self, queryset):
        if isinstance(queryset, list):
            names = [i.name for i in queryset]
            execution_qs = CeleryTaskExecution.objects.filter(name__in=names)
        else:
            execution_qs = CeleryTaskExecution.objects.all()
        summary_state_dict = self.generate_summary_state(execution_qs)
        for i in queryset:
            i.summary = summary_state_dict.get(i.name, {}).get('summary', {})
            i.state = summary_state_dict.get(i.name, {}).get('state', 'green')
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            page = self.generate_execute_time(page)
            page = self.loading_summary_state(page)
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        queryset = self.generate_execute_time(queryset)
        queryset = self.loading_summary_state(queryset)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CeleryTaskExecutionViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = CeleryTaskExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    queryset = CeleryTaskExecution.objects.all()
    search_fields = ('name',)

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            task = get_object_or_404(CeleryTask, id=task_id)
            self.queryset = self.queryset.filter(name=task.name)
        return self.queryset

    def create(self, request, *args, **kwargs):
        form_id = self.request.query_params.get('from', None)
        if not form_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        execution = get_object_or_404(CeleryTaskExecution, id=form_id)
        task = app.tasks.get(execution.name, None)
        if not task:
            msg = _("Task {} not found").format(execution.name)
            raise JMSException(code='task_not_found_error', detail=msg)
        try:
            t = task.delay(*execution.args, **execution.kwargs)
        except TypeError:
            msg = _("Task {} args or kwargs error").format(execution.name)
            raise JMSException(code='task_args_error', detail=msg)
        return Response(status=status.HTTP_201_CREATED, data={'task_id': t.id})
