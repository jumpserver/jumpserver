from django.db import transaction
from rest_framework import serializers

from common.drf.fields import ReadableHiddenField
from ops.models import Job, JobExecution

_all_ = []


class JobSerializer(serializers.ModelSerializer):
    owner = ReadableHiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Job
        fields = [
            "id", "name", "instant", "type", "module", "args", "playbook", "assets", "runas_policy", "runas", "owner",
            "date_created",
            "date_updated"
        ]


class JobExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobExecution
        read_only_fields = ["id", "task_id", "timedelta", "time_cost", 'is_finished', 'date_start', 'date_created',
                            'is_success', 'task_id', 'short_id']
        fields = read_only_fields + [
            "job"
        ]
