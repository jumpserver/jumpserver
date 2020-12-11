# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers
from django.shortcuts import reverse

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Task, AdHoc, AdHocExecution, CommandExecution


class AdHocExecutionSerializer(serializers.ModelSerializer):
    stat = serializers.SerializerMethodField()
    last_success = serializers.ListField(source='success_hosts')
    last_failure = serializers.DictField(source='failed_hosts')

    class Meta:
        model = AdHocExecution
        fields = [
            'id', 'task', 'task_display', 'hosts_amount', 'adhoc', 'date_start', 'stat',
            'date_finished', 'timedelta', 'is_finished', 'is_success', 'result', 'summary',
            'short_id', 'adhoc_short_id', 'last_success', 'last_failure'
        ]

    @staticmethod
    def get_task(obj):
        return obj.task.id

    @staticmethod
    def get_stat(obj):
        count_failed_hosts = len(obj.failed_hosts)
        count_success_hosts = len(obj.success_hosts)
        count_total = count_success_hosts + count_failed_hosts
        return {
            "total": count_total,
            "success": count_success_hosts,
            "failed": count_failed_hosts
        }


class AdHocExecutionExcludeResultSerializer(AdHocExecutionSerializer):
    class Meta:
        model = AdHocExecution
        fields = [
            'id', 'task', 'task_display', 'hosts_amount', 'adhoc', 'date_start', 'stat',
            'date_finished', 'timedelta', 'is_finished', 'is_success',
            'short_id', 'adhoc_short_id', 'last_success', 'last_failure'
        ]


class TaskSerializer(BulkOrgResourceModelSerializer):
    summary = serializers.ReadOnlyField(source='history_summary')
    latest_execution = AdHocExecutionExcludeResultSerializer(read_only=True)

    class Meta:
        model = Task
        fields = [
            'id', 'name', 'interval', 'crontab', 'is_periodic',
            'is_deleted', 'comment', 'date_created',
            'date_updated', 'latest_execution', 'summary',
        ]
        read_only_fields = [
            'is_deleted', 'date_created', 'date_updated',
            'latest_adhoc', 'latest_execution', 'total_run_amount',
            'success_run_amount', 'summary',
        ]


class TaskDetailSerializer(TaskSerializer):
    contents = serializers.ListField(source='latest_adhoc.tasks')

    class Meta(TaskSerializer.Meta):
        fields = TaskSerializer.Meta.fields + ['contents']


class AdHocSerializer(serializers.ModelSerializer):
    become_display = serializers.ReadOnlyField()
    tasks = serializers.ListField()

    class Meta:
        model = AdHoc
        fields = [
            "id", "task", 'tasks', "pattern", "options",
            "hosts", "run_as_admin", "run_as", "become",
            "date_created", "short_id",
            "become_display",
        ]
        read_only_fields = [
            'date_created'
        ]
        extra_kwargs = {
            "become": {'write_only': True}
        }


class AdHocExecutionNestSerializer(serializers.ModelSerializer):
    last_success = serializers.ListField(source='success_hosts')
    last_failure = serializers.DictField(source='failed_hosts')
    last_run = serializers.CharField(source='short_id')

    class Meta:
        model = AdHocExecution
        fields = (
            'last_success', 'last_failure', 'last_run', 'timedelta', 'is_finished',
            'is_success'
        )


class AdHocDetailSerializer(AdHocSerializer):
    latest_execution = AdHocExecutionNestSerializer(allow_null=True)
    task_name = serializers.CharField(source='task.name')

    class Meta(AdHocSerializer.Meta):
        fields = AdHocSerializer.Meta.fields + [
            'latest_execution', 'created_by', 'run_times', 'task_name'
        ]


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
        ref_name = 'OpsCommandExecution'

    @staticmethod
    def get_log_url(obj):
        return reverse('api-ops:celery-task-log', kwargs={'pk': obj.id})

