from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from ops.api.base import SelfBulkModelViewSet
from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer

__all__ = ['JobViewSet', 'JobExecutionViewSet', 'JobRunVariableHelpAPIView', 'JobAssetDetail']

from ops.tasks import run_ops_job_execution
from ops.variables import JMS_JOB_VARIABLE_HELP


def set_task_to_serializer_data(serializer, task):
    data = getattr(serializer, "_data", {})
    data["task_id"] = task.id
    setattr(serializer, "_data", data)


class JobViewSet(SelfBulkModelViewSet):
    serializer_class = JobSerializer
    permission_classes = ()
    model = Job

    def get_queryset(self):
        query_set = super().get_queryset()
        if self.action != 'retrieve':
            return query_set.filter(instant=False)
        return query_set

    def perform_create(self, serializer):
        instance = serializer.save()
        run_after_save = serializer.validated_data.get('run_after_save', False)
        if instance.instant or run_after_save:
            self.run_job(instance, serializer)

    def perform_update(self, serializer):
        instance = serializer.save()
        run_after_save = serializer.validated_data.get('run_after_save', False)
        if run_after_save:
            self.run_job(instance, serializer)

    @staticmethod
    def run_job(job, serializer):
        execution = job.create_execution()
        task = run_ops_job_execution.delay(execution.id)
        set_task_to_serializer_data(serializer, task)


class JobExecutionViewSet(SelfBulkModelViewSet):
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


class JobRunVariableHelpAPIView(APIView):
    rbac_perms = ()
    permission_classes = ()

    def get(self, request, **kwargs):
        return Response(data=JMS_JOB_VARIABLE_HELP)


class JobAssetDetail(APIView):
    rbac_perms = ()
    permission_classes = ()

    def get(self, request, **kwargs):
        execution_id = request.query_params.get('execution_id')
        if execution_id:
            execution = get_object_or_404(JobExecution, id=execution_id)
            return Response(data=execution.assent_result_detail)
