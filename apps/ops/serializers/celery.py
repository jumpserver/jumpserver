# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from rest_framework import serializers

from ops.celery import app
from ops.models import CeleryTask, CeleryTaskExecution

__all__ = [
    'CeleryResultSerializer', 'CeleryTaskExecutionSerializer',
    'CeleryPeriodTaskSerializer', 'CeleryTaskSerializer'
]


class CeleryResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    result = serializers.JSONField()
    state = serializers.CharField(max_length=16)


class CeleryPeriodTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTask
        fields = [
            'name', 'task', 'enabled', 'description',
            'last_run_at', 'total_run_count'
        ]


class CeleryTaskSerializer(serializers.ModelSerializer):
    exec_cycle = serializers.CharField(read_only=True)
    next_exec_time = serializers.DateTimeField(format="%Y/%m/%d %H:%M:%S", read_only=True)

    class Meta:
        model = CeleryTask
        read_only_fields = [
            'id', 'name', 'meta', 'summary', 'state',
            'date_last_publish', 'exec_cycle', 'next_exec_time'
        ]
        fields = read_only_fields


class CeleryTaskExecutionSerializer(serializers.ModelSerializer):
    is_success = serializers.BooleanField(required=False, read_only=True, label=_('Success'))
    task_name = serializers.SerializerMethodField()

    class Meta:
        model = CeleryTaskExecution
        fields = [
            "id", "name", "task_name", "args", "kwargs", "time_cost", "timedelta",
            "is_success", "is_finished", "date_published",
            "date_start", "date_finished"
        ]

    @staticmethod
    def get_task_name(obj):
        from assets.const import AutomationTypes as AssetTypes
        from accounts.const import AutomationTypes as AccountTypes
        tp_dict = dict(AssetTypes.choices) | dict(AccountTypes.choices)
        tp = obj.kwargs.get('tp')
        task = app.tasks.get(obj.name)
        task_name = getattr(task, 'verbose_name', obj.name)
        if tp:
            task_name = f'{task_name}({tp_dict.get(tp, tp)})'
        return task_name
