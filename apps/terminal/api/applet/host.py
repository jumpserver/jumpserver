from rest_framework import viewsets

from terminal import serializers, models

__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(viewsets.ModelViewSet):
    queryset = models.AppletHost.objects.all()
    serializer_class = serializers.AppletHostSerializer


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    queryset = models.AppletHostDeployment.objects.all()
    serializer_class = serializers.AppletHostDeploymentSerializer

