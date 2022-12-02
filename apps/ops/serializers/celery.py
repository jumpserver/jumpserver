# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers

from django_celery_beat.models import PeriodicTask

__all__ = [
    'CeleryResultSerializer', 'CeleryTaskExecutionSerializer',
    'CeleryPeriodTaskSerializer', 'CeleryTaskSerializer'
]

from ops.models import CeleryTask, CeleryTaskExecution


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
    class Meta:
        model = CeleryTask
        read_only_fields = ['id', 'name', 'meta', 'summary', 'state', 'last_published_time']
        fields = read_only_fields


class CeleryTaskExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CeleryTaskExecution
        fields = [
            "id", "name", "args", "kwargs", "time_cost", "timedelta", "state", "is_finished", "date_published",
            "date_start",
            "date_finished"
        ]
