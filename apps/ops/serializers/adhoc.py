# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers
from django.shortcuts import reverse

from ..models import Task, AdHoc, AdHocRunHistory, CommandExecution


class AdHocRunHistorySerializer(serializers.ModelSerializer):
    stat = serializers.SerializerMethodField()

    class Meta:
        model = AdHocRunHistory
        fields = '__all__'

    @staticmethod
    def get_task(obj):
        return obj.task.id

    @staticmethod
    def get_stat(obj):
        return {
            "total": obj.hosts_amount,
            "success": len(obj.summary.get("contacted", [])),
            "failed": len(obj.summary.get("dark", [])),
        }

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['short_id', 'adhoc_short_id'])
        return fields


class AdHocRunHistoryExcludeResultSerializer(AdHocRunHistorySerializer):
    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields = [i for i in fields if i not in ['result', 'summary']]
        return fields


class TaskSerializer(serializers.ModelSerializer):
    latest_history = AdHocRunHistoryExcludeResultSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'interval', 'crontab', 'is_periodic',
            'is_deleted', 'comment', 'created_by', 'date_created',
            'date_updated', 'latest_history',
        ]
        read_only_fields = [
            'is_deleted', 'created_by', 'date_created', 'date_updated',
            'latest_adhoc', 'latest_history', 'total_run_amount',
            'success_run_amount',
        ]


class AdHocSerializer(serializers.ModelSerializer):
    become_display = serializers.ReadOnlyField()

    class Meta:
        model = AdHoc
        fields = [
            "id", "task", 'tasks', "pattern", "options",
            "hosts", "run_as_admin", "run_as", "become",
            "created_by", "date_created", "short_id",
            "become_display",
        ]
        read_only_fields = [
            'created_by', 'date_created'
        ]
        extra_kwargs = {
            "become": {'write_only': True}
        }


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

