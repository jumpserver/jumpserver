from rest_framework import viewsets
from rest_framework.decorators import action

from orgs.utils import tmp_to_root_org
from orgs.models import Organization
from assets.models import Host
from terminal import serializers, models

__all__ = ['AppletHostViewSet', 'AppletHostDeploymentViewSet']


class AppletHostViewSet(viewsets.ModelViewSet):
    queryset = models.AppletHost.objects.all()
    serializer_class = serializers.AppletHostSerializer

    @action(methods=['get'], detail=False)
    def hosts(self, request):
        with tmp_to_root_org():
            kwargs = {
                'platform__name': 'RemoteAppHost',
                'org_id': Organization.SYSTEM_ID
            }
            return Host.objects.filter(**kwargs)


class AppletHostDeploymentViewSet(viewsets.ModelViewSet):
    queryset = models.AppletHostDeployment.objects.all()
    serializer_class = serializers.AppletHostDeploymentSerializer

