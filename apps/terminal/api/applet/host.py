from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.permissions import IsServiceAccount
from common.drf.api import JMSModelViewSet
from terminal.serializers import (
    AppletHostSerializer, AppletHostDeploymentSerializer,
    AppletHostStartupSerializer
)
from terminal.models import AppletHost, AppletHostDeployment
from terminal.tasks import run_applet_host_deployment


__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(JMSModelViewSet):
    serializer_class = AppletHostSerializer
    queryset = AppletHost.objects.all()

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


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = AppletHostDeploymentSerializer
    queryset = AppletHostDeployment.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        task = run_applet_host_deployment.delay(instance.id)
        return Response({'task': str(task.id)}, status=201)

