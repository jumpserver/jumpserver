import uuid

from django.db import transaction
from rest_framework import status
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api import JMSBulkModelViewSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppletHost, AppletHostDeployment
from terminal.serializers import (
    AppletHostSerializer, AppletHostDeploymentSerializer, AppletHostStartupSerializer
)
from terminal.tasks import run_applet_host_deployment, run_applet_host_deployment_install_applet

__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(JMSBulkModelViewSet):
    serializer_class = AppletHostSerializer
    queryset = AppletHost.objects.all()
    search_fields = ['asset_ptr__name', 'asset_ptr__address', ]
    rbac_perms = {
        'generate_accounts': 'terminal.change_applethost',
    }

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'startup':
            return [IsServiceAccount()]
        return super().get_permissions()

    @action(methods=['post'], detail=True, serializer_class=AppletHostStartupSerializer)
    def startup(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance.check_terminal_binding(request)
        return Response({'msg': 'ok'})

    @action(methods=['put'], detail=True, url_path='generate-accounts')
    def generate_accounts(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.generate_accounts()
        return Response({'msg': 'ok'})


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = AppletHostDeploymentSerializer
    queryset = AppletHostDeployment.objects.all()
    filterset_fields = ['host', ]
    rbac_perms = (
        ('applets', 'terminal.view_AppletHostDeployment'),
    )

    @staticmethod
    def start_deploy(instance):
        task = run_applet_host_deployment.apply_async((instance.id,), task_id=str(instance.id))

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        instance.save_task(instance.id)
        transaction.on_commit(lambda: self.start_deploy(instance))
        return Response({'task': str(instance.id)}, status=201)

    @action(methods=['post'], detail=False)
    def applets(self, request, *args, **kwargs):
        hosts = request.data.get('hosts', [])
        applet_id = request.data.get('applet_id', '')
        model = self.get_queryset().model
        hosts_qs = AppletHost.objects.filter(id__in=hosts)
        if not hosts_qs.exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        objs = [model(host=host) for host in hosts_qs]
        applet_host_deployments = model.objects.bulk_create(objs)
        applet_host_deployment_ids = [str(obj.id) for obj in applet_host_deployments]
        task_id = str(uuid.uuid4())
        model.objects.filter(id__in=applet_host_deployment_ids).update(task=task_id)
        transaction.on_commit(lambda: self.start_install_applet(applet_host_deployment_ids, applet_id, task_id))
        return Response({'task': task_id}, status=201)

    @staticmethod
    def start_install_applet(applet_host_deployment_ids, applet_id, task_id):
        run_applet_host_deployment_install_applet.apply_async((applet_host_deployment_ids, applet_id),
                                                              task_id=str(task_id))
