# ~*~ coding: utf-8 ~*~

from rest_framework.views import APIView, Response
from django.views.generic.detail import SingleObjectMixin

from common.utils import get_logger
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from orgs.mixins.api import OrgBulkModelViewSet
from ..models import Domain, Gateway
from .. import serializers


logger = get_logger(__file__)
__all__ = ['DomainViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class DomainViewSet(OrgBulkModelViewSet):
    model = Domain
    filter_fields = ("name", )
    search_fields = filter_fields
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.DomainSerializer

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.DomainWithGatewaySerializer
        return super().get_serializer_class()


class GatewayViewSet(OrgBulkModelViewSet):
    model = Gateway
    filter_fields = ("domain__name", "name", "username", "ip", "domain")
    search_fields = ("domain__name", "name", "username", "ip")
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.GatewaySerializer


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    permission_classes = (IsOrgAdmin,)
    object = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(Gateway.objects.all())
        local_port = self.request.data.get('port') or self.object.port
        ok, e = self.object.test_connective(local_port=local_port)
        if ok:
            return Response("ok")
        else:
            return Response({"error": e}, status=400)
