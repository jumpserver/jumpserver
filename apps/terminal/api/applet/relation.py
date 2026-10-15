from typing import Callable

from rest_framework.request import Request
from rest_framework.decorators import action
from rest_framework.response import Response

from common.api import JMSModelViewSet
from common.permissions import IsServiceAccount
from common.utils import is_uuid
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppletHost
from accounts.models import Account
from terminal.models import AppletPublication
from terminal.serializers import (
    AppletHostAccountSerializer,
    AppletPublicationSerializer,
    AppletHostAppletReportSerializer,
)


class HostMixin:
    request: Request
    permission_denied: Callable
    kwargs: dict
    page_no_limit = True
    permission_classes = [IsServiceAccount]

    def check_permissions(self, request):
        super().check_permissions(request)
        # Validate the binding for every action, including create and reports.
        host = self.host
        host_id = self.kwargs.get('host')
        if host_id and str(host.id) != str(host_id):
            self.permission_denied(self.request, 'User cannot access this applet host')

    def self_host(self):
        try:
            return self.request.user.terminal.applet_host
        except AttributeError:
            self.permission_denied(self.request, 'User has no applet host')

    @property
    def host(self):
        return self.self_host()


class AppletHostAccountsViewSet(HostMixin, JMSModelViewSet):
    serializer_class = AppletHostAccountSerializer
    queryset = Account.objects.none()

    def get_queryset(self):
        with tmp_to_builtin_org(system=1):
            queryset = self.host.accounts.all()
        return queryset

    def perform_create(self, serializer):
        with tmp_to_builtin_org(system=1):
            serializer.save(asset=self.host)


class AppletHostAppletViewSet(HostMixin, JMSModelViewSet):
    host: AppletHost
    serializer_class = AppletPublicationSerializer
    queryset = AppletPublication.objects.none()

    def get_object(self):
        pk = self.kwargs.get('pk')
        if not is_uuid(pk):
            return self.host.publications.get(applet__name=pk)
        else:
            return self.host.publications.get(pk=pk)

    def get_queryset(self):
        queryset = self.host.publications.all()
        return queryset

    def perform_create(self, serializer):
        serializer.save(host=self.host)

    def perform_update(self, serializer):
        serializer.save(host=self.host)

    @action(methods=['post'], detail=False)
    def reports(self, request, *args, **kwargs):
        serializer = AppletHostAppletReportSerializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        self.host.check_applets_state(data)
        publications = self.host.publications.all()
        serializer = AppletPublicationSerializer(publications, many=True)
        return Response(serializer.data)
