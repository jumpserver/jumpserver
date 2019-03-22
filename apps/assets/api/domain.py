# ~*~ coding: utf-8 ~*~

from rest_framework_bulk import BulkModelViewSet
from rest_framework.views import APIView, Response
from rest_framework.pagination import LimitOffsetPagination

from django.views.generic.detail import SingleObjectMixin

from common.utils import get_logger
from common.permissions import IsOrgAdmin, IsAppUser, IsOrgAdminOrAppUser
from ..models import Domain, Gateway
from .. import serializers


logger = get_logger(__file__)
__all__ = ['DomainViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class DomainViewSet(BulkModelViewSet):
    queryset = Domain.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.DomainSerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset().all()
        return queryset

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.DomainWithGatewaySerializer
        return super().get_serializer_class()

    def get_permissions(self):
        if self.request.query_params.get('gateway'):
            self.permission_classes = (IsOrgAdminOrAppUser,)
        return super().get_permissions()


class GatewayViewSet(BulkModelViewSet):
    filter_fields = ("domain__name", "name", "username", "ip", "domain")
    search_fields = filter_fields
    queryset = Gateway.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.GatewaySerializer
    pagination_class = LimitOffsetPagination


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    permission_classes = (IsOrgAdmin,)
    model = Gateway
    object = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object(Gateway.objects.all())
        local_port = self.request.data.get('port') or self.object.port
        ok, e = self.object.test_connective(local_port=local_port)
        if ok:
            return Response("ok")
        else:
            return Response({"failed": e}, status=404)
