from django.db.models import Count
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer

__all__ = ['JobViewSet', 'JobExecutionViewSet', 'JobRunVariableHelpAPIView',
           'JobAssetDetail', 'JobExecutionTaskDetail','FrequentUsernames']

from ops.tasks import run_ops_job_execution
from ops.variables import JMS_JOB_VARIABLE_HELP
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_org, get_current_org_id, get_current_org
from assets.models import Account


def set_task_to_serializer_data(serializer, task):
    data = getattr(serializer, "_data", {})
    data["task_id"] = task.id
    setattr(serializer, "_data", data)


class JobViewSet(OrgBulkModelViewSet):
    serializer_class = JobSerializer
    permission_classes = ()
    model = Job

    def allow_bulk_destroy(self, qs, filtered):
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        if self.action != 'retrieve':
            return queryset.filter(instant=False)
        return queryset

    def perform_create(self, serializer):
        run_after_save = serializer.validated_data.pop('run_after_save', False)
        instance = serializer.save()
        if instance.instant or run_after_save:
            self.run_job(instance, serializer)

    def perform_update(self, serializer):
        run_after_save = serializer.validated_data.pop('run_after_save', False)
        instance = serializer.save()
        if run_after_save:
            self.run_job(instance, serializer)

    def run_job(self, job, serializer):
        execution = job.create_execution()
        execution.creator = self.request.user
        execution.save()
        task = run_ops_job_execution.delay(execution.id)
        set_task_to_serializer_data(serializer, task)


class JobExecutionViewSet(OrgBulkModelViewSet):
    serializer_class = JobExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    permission_classes = ()
    model = JobExecution

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.job_version = instance.job.version
        instance.creator = self.request.user
        instance.save()
        task = run_ops_job_execution.delay(instance.id)
        set_task_to_serializer_data(serializer, task)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        job_id = self.request.query_params.get('job_id')
        if job_id:
            queryset = queryset.filter(job_id=job_id)
        return queryset


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


class JobExecutionTaskDetail(APIView):
    rbac_perms = ()
    permission_classes = ()

    def get(self, request, **kwargs):
        org = get_current_org()
        task_id = request.query_params.get('task_id')
        if task_id:
            with tmp_to_org(org):
                execution = get_object_or_404(JobExecution, task_id=task_id)
                return Response(data={
                    'is_finished': execution.is_finished,
                    'is_success': execution.is_success,
                    'time_cost': execution.time_cost,
                })


class FrequentUsernames(APIView):
    rbac_perms = ()
    permission_classes = ()

    def get(self, request, **kwargs):
        top_accounts = Account.objects.all().values('username').annotate(total=Count('username')).order_by('total')
        return Response(data=top_accounts)
