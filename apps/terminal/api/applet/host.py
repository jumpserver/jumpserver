from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from orgs.utils import tmp_to_builtin_org
from terminal import serializers
from terminal.models import AppletHost, Applet
from terminal.tasks import run_applet_host_deployment

__all__ = ['AppletHostViewSet']


class AppletHostViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.AppletHostSerializer

    def get_queryset(self):
        return AppletHost.objects.all()

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    @action(methods=['post'], detail=True)
    def deploy(self, request):
        from terminal.automations.deploy_applet_host.manager import DeployAppletHostManager
        manager = DeployAppletHostManager(self)
        manager.run()

    @action(methods=['get'], detail=True, url_path='')
    def not_published_applets(self, request, *args, **kwargs):
        instance = self.get_object()
        applets = Applet.objects.exclude(id__in=instance.applets.all())
        serializer = serializers.AppletSerializer(applets, many=True)
        return Response(serializer.data)

