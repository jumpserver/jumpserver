# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from rest_framework import serializers
from django.shortcuts import reverse

from ..models import AdHoc, AdHocExecution


class AdHocExecutionSerializer(serializers.ModelSerializer):
    stat = serializers.SerializerMethodField()
    last_success = serializers.ListField(source='success_hosts')
    last_failure = serializers.DictField(source='failed_hosts')

    class Meta:
        model = AdHocExecution
        fields_mini = ['id']
        fields_small = fields_mini + [
            'hosts_amount', 'timedelta', 'result', 'summary', 'short_id',
            'is_finished', 'is_success',
            'date_start', 'date_finished',
        ]
        fields_fk = ['task', 'task_display', 'adhoc', 'adhoc_short_id',]
        fields_custom = ['stat', 'last_success', 'last_failure']
        fields = fields_small + fields_fk + fields_custom

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


class AdHocSerializer(serializers.ModelSerializer):
    become_display = serializers.ReadOnlyField()
    tasks = serializers.ListField()

    class Meta:
        model = AdHoc
        fields_mini = ['id']
        fields_small = fields_mini + [
            'tasks', "pattern", "options", "run_as",
            "become", "become_display", "short_id",
            "run_as_admin",
            "date_created",
        ]
        fields_fk = ["task"]
        fields_m2m = ["hosts"]
        fields = fields_small + fields_fk + fields_m2m
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
            'last_success', 'last_failure', 'last_run', 'timedelta',
            'is_finished', 'is_success'
        )


class AdHocDetailSerializer(AdHocSerializer):
    latest_execution = AdHocExecutionNestSerializer(allow_null=True)
    task_name = serializers.CharField(source='task.name')

    class Meta(AdHocSerializer.Meta):
        fields = AdHocSerializer.Meta.fields + [
            'latest_execution', 'created_by', 'run_times', 'task_name'
        ]


# class CommandExecutionSerializer(serializers.ModelSerializer):
#     result = serializers.JSONField(read_only=True)
#     log_url = serializers.SerializerMethodField()
#
#     class Meta:
#         model = CommandExecution
#         fields_mini = ['id']
#         fields_small = fields_mini + [
#             'command', 'result', 'log_url',
#             'is_finished', 'date_created', 'date_finished'
#         ]
#         fields_m2m = ['hosts']
#         fields = fields_small + fields_m2m
#         read_only_fields = [
#             'result', 'is_finished', 'log_url', 'date_created',
#             'date_finished'
#         ]
#         ref_name = 'OpsCommandExecution'
#
#     @staticmethod
#     def get_log_url(obj):
#         return reverse('api-ops:celery-task-log', kwargs={'pk': obj.id})

