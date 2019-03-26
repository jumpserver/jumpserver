# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers
from django.shortcuts import reverse

from .models import Task, AdHoc, AdHocRunHistory, CommandExecution


class CeleryResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    result = serializers.JSONField()
    state = serializers.CharField(max_length=16)


class CeleryTaskSerializer(serializers.Serializer):
    pass


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class AdHocSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdHoc
        exclude = ('_tasks', '_options', '_hosts', '_become')

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['tasks', 'options', 'hosts', 'become', 'short_id'])
        return fields


class AdHocRunHistorySerializer(serializers.ModelSerializer):
    task = serializers.SerializerMethodField()
    adhoc_short_id = serializers.SerializerMethodField()
    stat = serializers.SerializerMethodField()

    class Meta:
        model = AdHocRunHistory
        exclude = ('_result', '_summary')

    @staticmethod
    def get_adhoc_short_id(obj):
        return obj.adhoc.short_id

    @staticmethod
    def get_task(obj):
        return obj.adhoc.task.id

    @staticmethod
    def get_stat(obj):
        return {
            "total": obj.adhoc.hosts.count(),
            "success": len(obj.summary.get("contacted", [])),
            "failed": len(obj.summary.get("dark", [])),
        }

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['summary', 'short_id'])
        return fields


class CommandExecutionSerializer(serializers.ModelSerializer):
    result = serializers.JSONField(read_only=True)
    log_url = serializers.SerializerMethodField()

    class Meta:
        model = CommandExecution
        fields = [
            'id', 'hosts', 'run_as', 'command', 'result', 'log_url',
            'is_finished', 'date_created', 'date_finished'
        ]
        read_only_fields = [
            'result', 'is_finished', 'log_url', 'date_created',
            'date_finished'
        ]

    @staticmethod
    def get_log_url(obj):
        return reverse('api-ops:celery-task-log', kwargs={'pk': obj.id})
