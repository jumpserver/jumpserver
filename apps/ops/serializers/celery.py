# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import os

from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from rest_framework import serializers

from ops.celery import app
from ops.ansible.utils import get_ansible_task_log_path
from ops.models import CeleryTask, CeleryTaskExecution

__all__ = [
    'CeleryTaskExecutionSerializer', 'CeleryPeriodTaskSerializer',
    'CeleryTaskSerializer'
]


class CeleryPeriodTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTask
        read_only_fields = ['name', 'task', 'description',
                            'last_run_at', 'total_run_count']
        fields = ['enabled'] + read_only_fields


class CeleryTaskSerializer(serializers.ModelSerializer):
    enabled = serializers.BooleanField(required=False)
    exec_cycle = serializers.CharField(read_only=True, label=_('Execution cycle'))
    next_exec_time = serializers.DateTimeField(
        format="%Y/%m/%d %H:%M:%S", read_only=True, label=_('Next execution time')
    )

    class Meta:
        model = CeleryTask
        read_only_fields = [
            'id', 'name', 'meta', 'summary', 'state',
            'date_last_publish', 'exec_cycle', 'next_exec_time', 'enabled'
        ]
        fields = read_only_fields


class CeleryTaskExecutionSerializer(serializers.ModelSerializer):
    is_success = serializers.BooleanField(required=False, read_only=True, label=_('Success'))
    task_name = serializers.SerializerMethodField()
    has_ansible_log = serializers.SerializerMethodField()
    is_ansible_task = serializers.SerializerMethodField()

    class Meta:
        model = CeleryTaskExecution
        fields = [
            "id", "name", "task_name", "args", "kwargs", "time_cost", "timedelta",
            "state", "is_success", "is_finished", "date_published",
            "date_start", "date_finished", "has_ansible_log",
            "is_ansible_task",
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

    @staticmethod
    def get_has_ansible_log(obj):
        path = get_ansible_task_log_path(obj.id, create=False)
        return os.path.isfile(path)

    @staticmethod
    def get_is_ansible_task(obj):
        task = app.tasks.get(obj.name)
        return bool(task and getattr(task, 'queue', None) == 'ansible')
