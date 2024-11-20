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
from ops.serializers.job import (
    JobSerializer, JobExecutionSerializer, FileSerializer, JobTaskStopSerializer
)
from ops.utils import merge_nodes_and_assets

__all__ = [
    'JobViewSet', 'JobExecutionViewSet', 'JobRunVariableHelpAPIView', 'JobExecutionTaskDetail', 'UsernameHintsAPI'
]

from ops.tasks import run_ops_job_execution
from ops.variables import JMS_JOB_VARIABLE_HELP
from ops.const import COMMAND_EXECUTION_DISABLED
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import tmp_to_org, get_current_org
from accounts.models import Account
from assets.const import Protocol
from perms.const import ActionChoices
from perms.utils.asset_perm import PermAssetDetailUtil
from jumpserver.settings import get_file_md5


def set_task_to_serializer_data(serializer, task_id):
    data = getattr(serializer, "_data", {})
    data["task_id"] = task_id
    setattr(serializer, "_data", data)


class JobViewSet(OrgBulkModelViewSet):
    serializer_class = JobSerializer
    filterset_fields = ('name', 'type')
    search_fields = ('name', 'comment')
    model = Job
    _parameters = None

    def check_permissions(self, request):
        # job: upload_file
        if self.action == 'upload' or request.data.get('type') == Types.upload_file:
            return super().check_permissions(request)
        # job: adhoc, playbook
        if not settings.SECURITY_COMMAND_EXECUTION:
            return self.permission_denied(request, COMMAND_EXECUTION_DISABLED)
        return super().check_permissions(request)

    def check_upload_permission(self, assets, account_name):
        protocols_required = {Protocol.ssh, Protocol.sftp, Protocol.winrm}
        error_msg_missing_protocol = _(
            "Asset ({asset}) must have at least one of the following protocols added: SSH, SFTP, or WinRM")
        error_msg_auth_missing_protocol = _("Asset ({asset}) authorization is missing SSH, SFTP, or WinRM protocol")
        error_msg_auth_missing_upload = _("Asset ({asset}) authorization lacks upload permissions")
        for asset in assets:
            protocols = asset.protocols.values_list("name", flat=True)
            if not set(protocols).intersection(protocols_required):
                self.permission_denied(self.request, error_msg_missing_protocol.format(asset=asset.name))
            util = PermAssetDetailUtil(self.request.user, asset)
            if not util.check_perm_protocols(protocols_required):
                self.permission_denied(self.request, error_msg_auth_missing_protocol.format(asset=asset.name))
            if not util.check_perm_actions(account_name, [ActionChoices.upload.value]):
                self.permission_denied(self.request, error_msg_auth_missing_upload.format(asset=asset.name))

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset \
            .filter(creator=self.request.user) \
            .exclude(type=Types.upload_file)

        # Job 列表不显示 adhoc, retrieve 要取状态
        if self.action != 'retrieve':
            return queryset.filter(instant=False)
        return queryset

    def perform_create(self, serializer):
        run_after_save = serializer.validated_data.pop('run_after_save', False)
        self._parameters = serializer.validated_data.pop('parameters', None)
        nodes = serializer.validated_data.pop('nodes', [])
        assets = serializer.validated_data.get('assets', [])
        assets = merge_nodes_and_assets(nodes, assets, self.request.user)
        if serializer.validated_data.get('type') == Types.upload_file:
            account_name = serializer.validated_data.get('runas')
            self.check_upload_permission(assets, account_name)
        instance = serializer.save()

        if instance.instant or run_after_save:
            self.run_job(instance, serializer)

    def perform_update(self, serializer):
        run_after_save = serializer.validated_data.pop('run_after_save', False)
        self._parameters = serializer.validated_data.pop('parameters', None)
        instance = serializer.save()
        if run_after_save:
            self.run_job(instance, serializer)

    def run_job(self, job, serializer):
        execution = job.create_execution()
        if self._parameters:
            execution.parameters = JobExecutionSerializer.validate_parameters(self._parameters)
        execution.creator = self.request.user
        execution.save()

        set_task_to_serializer_data(serializer, execution.id)
        transaction.on_commit(
            lambda: run_ops_job_execution.apply_async(
                (str(execution.id),), task_id=str(execution.id)
            )
        )

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

    @action(methods=[POST], detail=False, serializer_class=FileSerializer,
            permission_classes=[IsValidUser, ], url_path='upload')
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
        upload_file_dir = safe_join(settings.SHARE_DIR, 'job_upload_file', job_id)
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

    def check_permissions(self, request):
        if not settings.SECURITY_COMMAND_EXECUTION:
            return self.permission_denied(request, COMMAND_EXECUTION_DISABLED)
        return super().check_permissions(request)

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
            user = request.user
            if user.has_perm("audits.view_joblog"):
                instance = get_object_or_404(JobExecution, pk=task_id)
            else:
                instance = get_object_or_404(JobExecution, pk=task_id, creator=request.user)
        except Http404:
            return Response(
                {'error': _('The task is being created and cannot be interrupted. Please try again later.')},
                status=400
            )
        try:
            task = AsyncResult(task_id, app=app)
            inspect = app.control.inspect()

            for worker in inspect.registered().keys():
                if not worker.startswith('ansible'):
                    continue
                if task_id not in [at['id'] for at in inspect.active().get(worker, [])]:
                    # 在队列中未执行使用revoke执行
                    task.revoke(terminate=True)
                    instance.set_error('Job stop by "revoke task {}"'.format(task_id))
                    return Response({'task_id': task_id}, status=200)
        except Exception as e:
            instance.set_error(str(e))
            return Response({'error': f'Error while stopping the task {task_id}: {e}'}, status=400)

        instance.stop()
        return Response({'task_id': task_id}, status=200)


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
            'status': {
                'value': execution.status,
                'label': execution.get_status_display()
            },
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
        node_ids = request.data.get('nodes', [])
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
                           .annotate(total=Count('username')) \
                           .order_by('-total', '-username')[:10]
        return Response(data=top_accounts)
