from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.drf.api import JMSModelViewSet
from orgs.utils import tmp_to_builtin_org
from terminal import serializers
from terminal.models import AppletHost, Applet, AppletHostDeployment
from terminal.tasks import run_applet_host_deployment


__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(JMSModelViewSet):
    serializer_class = serializers.AppletHostSerializer
    queryset = AppletHost.objects.all()
    rbac_perms = {
        'accounts': 'terminal.view_applethost',
        'reports': '*'
    }

    @action(methods=['post'], detail=True, serializer_class=serializers.AppletHostReportSerializer)
    def reports(self, request, *args, **kwargs):
        # 1. Host 和 Terminal 关联
        # 2. 上报 安装的 Applets 每小时
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        instance.check_terminal_binding(request)
        instance.check_applets_state(data['applets'])
        return Response({'msg': 'ok'})

    @action(methods=['get'], detail=True, serializer_class=serializers.AppletHostAccountSerializer)
    def accounts(self, request, *args, **kwargs):
        host = self.get_object()
        with tmp_to_builtin_org(system=1):
            accounts = host.accounts.all().filter(privileged=False)
        response = self.get_paginated_response_from_queryset(accounts)
        return response


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostDeploymentSerializer
    queryset = AppletHostDeployment.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        task = run_applet_host_deployment.delay(instance.id)
        return Response({'task': str(task.id)}, status=201)

