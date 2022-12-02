# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import datetime

from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from ..models import AdHoc, AdHocExecution


class AdHocSerializer(serializers.ModelSerializer):
    owner = ReadableHiddenField(default=serializers.CurrentUserDefault())
    row_count = serializers.IntegerField(read_only=True)
    size = serializers.IntegerField(read_only=True)

    class Meta:
        model = AdHoc
        fields = ["id", "name", "module", "row_count", "size", "args", "owner", "date_created", "date_updated"]


class AdHocExecutionSerializer(serializers.ModelSerializer):
    stat = serializers.SerializerMethodField()
    last_success = serializers.ListField(source='success_hosts')
    last_failure = serializers.DictField(source='failed_hosts')

    class Meta:
        model = AdHocExecution
        fields_mini = ['id']
        fields_small = fields_mini + [
            'timedelta', 'result', 'summary', 'short_id',
            'is_finished', 'is_success',
            'date_start', 'date_finished',
        ]
        fields_fk = ['task', 'task_display']
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
