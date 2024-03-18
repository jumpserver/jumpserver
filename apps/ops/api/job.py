import json
import os

from celery.result import AsyncResult
from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils._os import safe_join
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from assets.models import Asset
from common.const.http import POST
from common.permissions import IsValidUser
from ops.celery import app
from ops.const import Types
from ops.models import Job, JobExecution
from ops.serializers.job import JobSerializer, JobExecutionSerializer, FileSerializer, JobTaskStopSerializer

__all__ = [
    'JobViewSet', 'JobExecutionViewSet', 'JobRunVariableHelpAPIView',
    'JobAssetDetail', 'JobExecutionTaskDetail', 'UsernameHintsAPI'
]

from ops.tasks import run_ops_job_execution
from ops.variables import JMS_JOB_VARIABLE_HELP
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_org, get_current_org
from accounts.models import Account
from perms.models import PermNode
from perms.utils import UserPermAssetUtil
from jumpserver.settings import get_file_md5


def set_task_to_serializer_data(serializer, task_id):
    data = getattr(serializer, "_data", {})
    data["task_id"] = task_id
    setattr(serializer, "_data", data)


def merge_nodes_and_assets(nodes, assets, user):
    if nodes:
        perm_util = UserPermAssetUtil(user=user)
        for node_id in nodes:
            if node_id == PermNode.FAVORITE_NODE_KEY:
                node_assets = perm_util.get_favorite_assets()
            elif node_id == PermNode.UNGROUPED_NODE_KEY:
                node_assets = perm_util.get_ungroup_assets()
            else:
                node, node_assets = perm_util.get_node_all_assets(node_id)
            assets.extend(node_assets.exclude(id__in=[asset.id for asset in assets]))
    return assets


class JobViewSet(OrgBulkModelViewSet):
    serializer_class = JobSerializer
    search_fields = ('name', 'comment')
    model = Job

    def check_permissions(self, request):
        if not settings.SECURITY_COMMAND_EXECUTION:
            return self.permission_denied(request, "Command execution disabled")
        return super().check_permissions(request)

    def allow_bulk_destroy(self, qs, filtered):
        return True

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user).exclude(type=Types.upload_file)
        if self.action != 'retrieve':
            return queryset.filter(instant=False)
        return queryset

    def perform_create(self, serializer):
        run_after_save = serializer.validated_data.pop('run_after_save', False)
        node_ids = serializer.validated_data.pop('nodes', [])
        assets = serializer.validated_data.__getitem__('assets')
        assets = merge_nodes_and_assets(node_ids, assets, self.request.user)
        serializer.validated_data.__setitem__('assets', assets)
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

        set_task_to_serializer_data(serializer, execution.id)
        transaction.on_commit(
            lambda: run_ops_job_execution.apply_async((str(execution.id),), task_id=str(execution.id)))

    @staticmethod
    def get_duplicates_files(files):
        seen = set()
        duplicates = set()
        for file in files:
            if file in seen:
                duplicates.add(file)
            else:
                seen.add(file)
        return list(duplicates)

    @staticmethod
    def get_exceeds_limit_files(files):
        exceeds_limit_files = []
        for file in files:
            if file.size > settings.FILE_UPLOAD_SIZE_LIMIT_MB * 1024 * 1024:
                exceeds_limit_files.append(file)
        return exceeds_limit_files

    @action(methods=[POST], detail=False, serializer_class=FileSerializer, permission_classes=[IsValidUser, ],
            url_path='upload')
    def upload(self, request, *args, **kwargs):
        uploaded_files = request.FILES.getlist('files')
        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            msg = 'Upload data invalid: {}'.format(serializer.errors)
            return Response({'error': msg}, status=400)

        same_files = self.get_duplicates_files(uploaded_files)
        if same_files:
            return Response({'error': _("Duplicate file exists")}, status=400)

        exceeds_limit_files = self.get_exceeds_limit_files(uploaded_files)
        if exceeds_limit_files:
            return Response(
                {'error': _("File size exceeds maximum limit. Please select a file smaller than {limit}MB").format(
                    limit=settings.FILE_UPLOAD_SIZE_LIMIT_MB)},
                status=400)

        job_id = request.data.get('job_id', '')
        job = get_object_or_404(Job, pk=job_id, creator=request.user)
        job_args = json.loads(job.args)
        src_path_info = []
        upload_file_dir = safe_join(settings.DATA_DIR, 'job_upload_file', job_id)
        for uploaded_file in uploaded_files:
            filename = uploaded_file.name
            saved_path = safe_join(upload_file_dir, f'{filename}')
            os.makedirs(os.path.dirname(saved_path), exist_ok=True)
            with open(saved_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            src_path_info.append({'filename': filename, 'md5': get_file_md5(saved_path)})
        job_args['src_path_info'] = src_path_info
        job.args = json.dumps(job_args)
        job.save()
        self.run_job(job, serializer)
        return Response({'task_id': serializer.data.get('task_id')}, status=201)


class JobExecutionViewSet(OrgBulkModelViewSet):
    serializer_class = JobExecutionSerializer
    http_method_names = ('get', 'post', 'head', 'options',)
    model = JobExecution
    search_fields = ('material',)
    filterset_fields = ['status', 'job_id']

    @staticmethod
    def start_deploy(instance, serializer):
        run_ops_job_execution.apply_async((str(instance.id),), task_id=str(instance.id))

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.job_version = instance.job.version
        instance.material = instance.job.material
        instance.job_type = Types[instance.job.type].value
        instance.creator = self.request.user
        instance.save()

        set_task_to_serializer_data(serializer, instance.id)
        transaction.on_commit(
            lambda: run_ops_job_execution.apply_async((str(instance.id),), task_id=str(instance.id))
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(creator=self.request.user)
        return queryset

    @action(methods=[POST], detail=False, serializer_class=JobTaskStopSerializer, permission_classes=[IsValidUser, ],
            url_path='stop')
    def stop(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({'error': serializer.errors}, status=400)
        task_id = serializer.validated_data['task_id']
        try:
            instance = get_object_or_404(JobExecution, task_id=task_id, creator=request.user)
        except Http404:
            return Response(
                {'error': _('The task is being created and cannot be interrupted. Please try again later.')},
                status=400
            )

        task = AsyncResult(task_id, app=app)
        inspect = app.control.inspect()
        for worker in inspect.registered().keys():
            if task_id not in [at['id'] for at in inspect.active().get(worker, [])]:
                # 在队列中未执行使用revoke执行
                task.revoke(terminate=True)
                instance.set_error('Job stop by "revoke task {}"'.format(task_id))
                return Response({'task_id': task_id}, status=200)

        instance.stop()
        return Response({'task_id': task_id}, status=200)


class JobAssetDetail(APIView):
    rbac_perms = {
        'get': ['ops.view_jobexecution'],
    }

    def get(self, request, **kwargs):
        execution_id = request.query_params.get('execution_id', '')
        execution = get_object_or_404(JobExecution, id=execution_id, creator=request.user)
        return Response(data=execution.assent_result_detail)


class JobExecutionTaskDetail(APIView):
    rbac_perms = {
        'GET': ['ops.view_jobexecution'],
    }

    def get(self, request, **kwargs):
        org = get_current_org()
        task_id = str(kwargs.get('task_id'))

        with tmp_to_org(org):
            execution = get_object_or_404(JobExecution, pk=task_id, creator=request.user)

        return Response(data={
            'status': execution.status,
            'is_finished': execution.is_finished,
            'is_success': execution.is_success,
            'time_cost': execution.time_cost,
            'job_id': execution.job.id,
            'summary': execution.summary
        })


class JobRunVariableHelpAPIView(APIView):
    permission_classes = [IsValidUser]

    def get(self, request, **kwargs):
        return Response(data=JMS_JOB_VARIABLE_HELP)


class UsernameHintsAPI(APIView):
    permission_classes = [IsValidUser]

    def post(self, request, **kwargs):
        node_ids = request.data.get('nodes', None)
        asset_ids = request.data.get('assets', [])
        query = request.data.get('query', None)

        assets = list(Asset.objects.filter(id__in=asset_ids).all())

        assets = merge_nodes_and_assets(node_ids, assets, request.user)

        top_accounts = Account.objects \
                           .exclude(username__startswith='jms_') \
                           .exclude(username__startswith='js_') \
                           .filter(username__icontains=query) \
                           .filter(asset__in=assets) \
                           .values('username') \
                           .annotate(total=Count('username', distinct=True)) \
                           .order_by('total', '-username')[:10]
        return Response(data=top_accounts)
