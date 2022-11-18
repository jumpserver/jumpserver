from django.db import transaction
from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from ops.mixin import PeriodTaskSerializerMixin
from ops.models import Job, JobExecution

_all_ = []


class JobSerializer(serializers.ModelSerializer, PeriodTaskSerializerMixin):
    owner = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Job
        read_only_fields = ["id", "date_last_run", "date_created", "date_updated", "average_time_cost"]
        fields = read_only_fields + [
            "name", "instant", "type", "module", "args", "playbook", "assets", "runas_policy", "runas", "owner",
            "parameters_define",
            "timeout",
            "chdir",
            "comment",
            "summary",
            "is_periodic", "interval", "crontab"
        ]


class JobExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExecution
        read_only_fields = ["id", "task_id", "timedelta", "time_cost", 'is_finished', 'date_start', 'date_created',
                            'is_success', 'task_id', 'short_id']
        fields = read_only_fields + [
            "job", "parameters"
        ]
