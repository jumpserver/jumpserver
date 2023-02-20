# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.utils.translation import gettext_lazy as _
from django_celery_beat.models import PeriodicTask
from rest_framework import serializers

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
        read_only_fields = ['id', 'name', 'meta', 'summary', 'state', 'date_last_publish']
        fields = read_only_fields


class CeleryTaskExecutionSerializer(serializers.ModelSerializer):
    is_success = serializers.BooleanField(required=False, read_only=True, label=_('Success'))

    class Meta:
        model = CeleryTaskExecution
        fields = [
            "id", "name", "args", "kwargs", "time_cost", "timedelta",
            "is_success", "is_finished", "date_published",
            "date_start", "date_finished"
        ]
