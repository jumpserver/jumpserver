from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api import JMSBulkModelViewSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppletHost, AppletHostDeployment
from terminal.serializers import (
    AppletHostSerializer, AppletHostDeploymentSerializer,
    AppletHostStartupSerializer, AppletHostDeployAppletSerializer
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        task = run_applet_host_deployment.delay(instance.id)
        instance.save_task(task.id)
        return Response({'task': str(task.id)}, status=201)

    @action(methods=['post'], detail=False, serializer_class=AppletHostDeployAppletSerializer)
    def applets(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        applet_id = serializer.validated_data.pop('applet_id', '')
        instance = serializer.save()
        task = run_applet_host_deployment_install_applet.delay(instance.id, applet_id)
        instance.save_task(task.id)
        return Response({'task': str(task.id)}, status=201)
