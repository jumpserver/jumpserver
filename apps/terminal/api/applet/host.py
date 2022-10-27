from rest_framework import viewsets

from orgs.utils import tmp_to_builtin_org
from terminal import serializers, models

__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostSerializer

    def get_queryset(self):
        return models.AppletHost.objects.all()

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    queryset = models.AppletHostDeployment.objects.all()
    serializer_class = serializers.AppletHostDeploymentSerializer

