# -*- coding: utf-8 -*-
#
import re
import logging
from django.db.models import Count, F, Q, Window
from django.db.models.functions import RowNumber

from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.utils.translation import gettext as _, gettext_lazy
from django_celery_beat.models import PeriodicTask
from django_filters import rest_framework as drf_filters
from rest_framework import viewsets, mixins, status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from common.api import CommonApiMixin
from common.drf.filters import BaseFilterSet
from common.exceptions import JMSException
from common.utils.timezone import local_now
from common.utils.verify_code import VERIFY_CODE_TASKS
from ops.celery import app
from ..models import CeleryTaskExecution, CeleryTask
from ..serializers import CeleryPeriodTaskSerializer
from ..serializers.celery import CeleryTaskSerializer, CeleryTaskExecutionSerializer

__all__ = [
    'CeleryPeriodTaskViewSet', 'CeleryTaskViewSet',
    'CeleryTaskExecutionViewSet', 'CeleryMonitorAPIView', 'CeleryMonitorStopAPIView',
]

logger = logging.getLogger(__name__)


class CeleryPeriodTaskViewSet(CommonApiMixin, viewsets.ModelViewSet):
    queryset = PeriodicTask.objects.all()
    serializer_class = CeleryPeriodTaskSerializer
    http_method_names = ('get', 'head', 'options', 'patch')
    lookup_field = 'name'
    lookup_value_regex = r'[\w.@]+'

    def get_object(self):
        name = self.kwargs.get('name')
        obj = get_object_or_404(PeriodicTask, name=name)
        return obj


class CeleryMonitorAPIView(APIView):
    rbac_perms = {'GET': 'ops.view_taskmonitor', 'HEAD': 'ops.view_taskmonitor'}

    def get(self, request, *args, **kwargs):
        from ops.celery.monitor import get_monitor_snapshot
        response = Response(get_monitor_snapshot())
        response['Cache-Control'] = 'no-store'
        return response


class MonitorStopSerializer(serializers.Serializer):
    worker = serializers.RegexField(r'^[\w.@,:-]{1,255}$', max_length=255)
    task_id = serializers.RegexField(r'^[\w.:-]{1,128}$', max_length=128)
    mode = serializers.ChoiceField(choices=('waiting', 'running'))


class CeleryMonitorStopAPIView(APIView):
    rbac_perms = {'POST': 'ops.stop_taskmonitor'}

    def post(self, request, *args, **kwargs):
        serializer = MonitorStopSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        from ops.celery.monitor import CACHE_KEY, stop_worker_task
        result = stop_worker_task(data['worker'], data['task_id'], data['mode'])
        logger.info('Task monitor stop: user=%s task=%s worker=%s mode=%s result=%s',
                    request.user.pk, data['task_id'], data['worker'], data['mode'], result)
        code = status.HTTP_202_ACCEPTED if result in (
            'revoked', 'revoke_requested', 'termination_requested',
        ) else status.HTTP_409_CONFLICT
        if code == status.HTTP_202_ACCEPTED:
            try:
                cache.delete(CACHE_KEY)
            except Exception:
                logger.warning('Could not invalidate task monitor snapshot', exc_info=True)
        return Response({'status': result}, status=code, headers={'Cache-Control': 'no-store'})


class CeleryTaskFilterSet(BaseFilterSet):
    name = drf_filters.CharFilter(
        method='filter_name', label=gettext_lazy('Task name or comment')
    )

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
        fields = ['name']
        fields_operator = {
            'name': ('icontains',),
        }


class CeleryTaskViewSet(
    CommonApiMixin, mixins.RetrieveModelMixin,
    mixins.ListModelMixin, mixins.DestroyModelMixin,
    viewsets.GenericViewSet
):
    search_fields = ('name',)
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
        now = local_now()
        for i in queryset:
            task = getattr(i, 'periodic_obj', None)
            if not task:
                continue
            i.exec_cycle = self.extract_schedule(str(task.scheduler))
            last_run_at = task.last_run_at or now
            next_run_at = task.schedule.remaining_estimate(last_run_at)
            if next_run_at.total_seconds() < 0:
                next_run_at = task.schedule.remaining_estimate(now)
            i.next_exec_time = now + next_run_at
            i.enabled = task.enabled
        return queryset

    def generate_summary_state(self, execution_qs):
        model = self.get_queryset().model
        summaries = {
            row['name']: {'summary': {'total': row['total'], 'success': row['success']},
                          'state': 'green', 'states': []}
            for row in execution_qs.order_by().values('name').annotate(
                total=Count('id'), success=Count('id', filter=Q(state='SUCCESS')),
            )
        }
        # Bound Python memory to five states per displayed task. Window filtering
        # is supported by our Django and MariaDB/PostgreSQL minimum versions.
        recent = execution_qs.filter(name__in=summaries).order_by().annotate(
            position=Window(RowNumber(), partition_by=[F('name')],
                            order_by=[F('date_published').desc(), F('id').desc()]),
        ).filter(position__lte=5).order_by('name', 'position').values('name', 'state')
        for row in recent:
            summaries[row['name']]['states'].append(row['state'])
        for summary in summaries.values():
            summary['state'] = model.compute_state_color(summary.pop('states'))
        return summaries

    def loading_summary_state(self, queryset):
        names = [i.name for i in queryset]
        execution_qs = CeleryTaskExecution.objects.filter(name__in=names)
        summary_state_dict = self.generate_summary_state(execution_qs)
        for i in queryset:
            i.summary = summary_state_dict.get(i.name, {}).get('summary', {})
            i.state = summary_state_dict.get(i.name, {}).get('state', 'green')
        return queryset

    def filter_queryset(self, queryset):
        search = self.request.query_params.get('search')
        if search:
            queryset = CeleryTaskFilterSet.filter_name(queryset, 'name', search)
        else:
            queryset = super().filter_queryset(queryset)
        return queryset

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        queryset = self.mark_periodic_and_sorted(queryset)

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

    @staticmethod
    def mark_periodic_and_sorted(queryset):
        names = queryset.values_list('name', flat=True)
        periodic_tasks = PeriodicTask.objects.filter(name__in=names)
        periodic_task_dict = {task.task: task for task in periodic_tasks}
        for q in queryset:
            if q.name in periodic_task_dict:
                q.periodic_obj = periodic_task_dict[q.name]
                q.is_periodic = True
            else:
                q.is_periodic = False
        queryset = sorted(queryset, key=lambda x: x.is_periodic, reverse=True)
        return queryset


class CeleryTaskExecutionViewSet(CommonApiMixin, viewsets.ModelViewSet):
    serializer_class = CeleryTaskExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    queryset = CeleryTaskExecution.objects.all()
    search_fields = ('id',)

    def get_queryset(self):
        task_id = self.request.query_params.get('task_id')
        if task_id:
            task = get_object_or_404(CeleryTask, id=task_id)
            self.queryset = self.queryset.filter(name=task.name)
        if not self.request.user.is_superuser:
            self.queryset = self.queryset.filter(creator=self.request.user)
        return self.queryset

    def create(self, request, *args, **kwargs):
        form_id = self.request.query_params.get('from', None)
        if not form_id:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        execution = get_object_or_404(CeleryTaskExecution, id=form_id)
        # 按任务名拒绝重跑，覆盖旧记录和管理员；
        # 不能依赖去敏后参数缺失触发 TypeError 来阻止旧验证码重发。
        if execution.name in VERIFY_CODE_TASKS:
            raise JMSException(
                code='verify_code_task_rerun_forbidden',
                detail=_(
                    'Verification code tasks cannot be run again. '
                    'Please request a new code from the verification page.'
                )
            )
        task = app.tasks.get(execution.name, None)
        if not task:
            msg = _("Task {} not found").format(execution.name)
            raise JMSException(code='task_not_found_error', detail=msg)
        try:
            execution.kwargs.pop('__current_lang', None)
            execution.kwargs.pop('__current_org_id', None)
            t = task.delay(*execution.args, **execution.kwargs)
        except TypeError:
            msg = _("Task {} args or kwargs error").format(execution.name)
            raise JMSException(code='task_args_error', detail=msg)
        return Response(status=status.HTTP_201_CREATED, data={'task_id': t.id})
