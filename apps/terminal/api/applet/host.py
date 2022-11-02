from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from terminal import serializers
from terminal.models import AppletHost, Applet, AppletHostDeployment
from terminal.tasks import run_applet_host_deployment


__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostSerializer
    queryset = AppletHost.objects.all()

    @action(methods=['post'], detail=True)
    def report(self, request, *args, **kwargs):
        # TODO:
        # 1. 上报 安装的 Applets 每小时
        # 2. Host 和 Terminal 关联
        instance = self.get_object()
        instance.sync()
        return Response({'msg': 'ok'})

    @action(methods=['get'], detail=True)
    def accounts(self, request, *args, **kwargs):
        # TODO:
        # 1. 返回 host 上的所有用户, host 可以去创建和更新 每小时
        # 2. 密码长度最少 8 位，包含大小写字母和数字和特殊字符
        instance = self.get_object()
        return Response(instance.get_accounts())


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostDeploymentSerializer
    queryset = AppletHostDeployment.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        task = run_applet_host_deployment.delay(instance.id)
        return Response({'task': str(task.id)}, status=201)

