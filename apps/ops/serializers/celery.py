# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers

from django_celery_beat.models import PeriodicTask

__all__ = [
    'CeleryResultSerializer', 'CeleryTaskSerializer',
    'CeleryPeriodTaskSerializer'
]


class CeleryResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    result = serializers.JSONField()
    state = serializers.CharField(max_length=16)


class CeleryTaskSerializer(serializers.Serializer):
    pass


class CeleryPeriodTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodicTask
        fields = [
            'name', 'task', 'enabled', 'description',
            'last_run_at', 'total_run_count'
        ]
