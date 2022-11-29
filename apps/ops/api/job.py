from rest_framework import viewsets

from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer

__all__ = ['JobViewSet', 'JobExecutionViewSet']

from ops.tasks import run_ops_job_execution
from orgs.mixins.api import OrgBulkModelViewSet


def set_task_to_serializer_data(serializer, task):
    data = getattr(serializer, "_data", {})
    data["task_id"] = task.id
    setattr(serializer, "_data", data)


class JobViewSet(OrgBulkModelViewSet):
    serializer_class = JobSerializer
    model = Job
    permission_classes = ()

    def get_queryset(self):
        query_set = super().get_queryset()
        if self.action != 'retrieve':
            return query_set.filter(instant=False)
        return query_set

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.instant:
            execution = instance.create_execution()
            task = run_ops_job_execution.delay(execution.id)
            set_task_to_serializer_data(serializer, task)


class JobExecutionViewSet(OrgBulkModelViewSet):
    serializer_class = JobExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    permission_classes = ()
    model = JobExecution

    def perform_create(self, serializer):
        instance = serializer.save()
        task = run_ops_job_execution.delay(instance.id)
        set_task_to_serializer_data(serializer, task)

    def get_queryset(self):
        query_set = super().get_queryset()
        job_id = self.request.query_params.get('job_id')
        if job_id:
            query_set = query_set.filter(job_id=job_id)
        return query_set
