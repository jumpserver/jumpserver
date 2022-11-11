from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer

__all__ = ['JobViewSet', 'JobExecutionViewSet']

from ops.tasks import run_ops_job, run_ops_job_executions


class JobViewSet(viewsets.ModelViewSet):
    serializer_class = JobSerializer
    queryset = Job.objects.all()

    def get_queryset(self):
        return self.queryset.filter(instant=False)

    def perform_create(self, serializer):
        instance = serializer.save()
        if instance.instant:
            run_ops_job.delay(instance.id)


class JobExecutionViewSet(viewsets.ModelViewSet):
    serializer_class = JobExecutionSerializer
    queryset = JobExecution.objects.all()
    http_method_names = ('get', 'post', 'head', 'options',)

    def perform_create(self, serializer):
        instance = serializer.save()
        run_ops_job_executions.delay(instance.id)

    def get_queryset(self):
        job_id = self.request.query_params.get('job_id')
        job_type = self.request.query_params.get('type')
        if job_id:
            self.queryset = self.queryset.filter(job_id=job_id)
        if job_type:
            self.queryset = self.queryset.filter(job__type=job_type)
        return self.queryset
