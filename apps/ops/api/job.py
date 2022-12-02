from rest_framework import viewsets

from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer

__all__ = ['JobViewSet', 'JobExecutionViewSet']

from ops.tasks import run_ops_job, run_ops_job_executions
from orgs.mixins.api import OrgBulkModelViewSet


class JobViewSet(OrgBulkModelViewSet):
    serializer_class = JobSerializer
    model = Job
    permission_classes = ()

    def get_queryset(self):
        query_set = super().get_queryset()
        return query_set.filter(instant=False)

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.instant:
            run_ops_job.delay(instance.id)


class JobExecutionViewSet(OrgBulkModelViewSet):
    serializer_class = JobExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    # filter_fields = ('type',)
    permission_classes = ()
    model = JobExecution

    def perform_create(self, serializer):
        instance = serializer.save()
        run_ops_job_executions.delay(instance.id)

    def get_queryset(self):
        query_set = super().get_queryset()
        job_id = self.request.query_params.get('job_id')
        if job_id:
            self.queryset = query_set.filter(job_id=job_id)
        return query_set
