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


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostDeploymentSerializer
    queryset = AppletHostDeployment.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()
        task = run_applet_host_deployment.delay(instance.id)
        return Response({'task': str(task.id)}, status=201)

