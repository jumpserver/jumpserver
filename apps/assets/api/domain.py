# ~*~ coding: utf-8 ~*~
from django.db.models import F
from django.views.generic.detail import SingleObjectMixin
from django.utils.translation import ugettext as _
from rest_framework.views import APIView, Response
from rest_framework.serializers import ValidationError

from common.utils import get_logger
from orgs.mixins.api import OrgBulkModelViewSet
from ..models import Domain, Host
from .. import serializers

logger = get_logger(__file__)
__all__ = ['DomainViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class DomainViewSet(OrgBulkModelViewSet):
    model = Domain
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_class = serializers.DomainSerializer
    ordering_fields = ('name',)
    ordering = ('name',)

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.DomainWithGatewaySerializer
        return super().get_serializer_class()


class GatewayViewSet(OrgBulkModelViewSet):
    perm_model = Host
    filterset_fields = ("domain__name", "name", "domain")
    search_fields = ("domain__name",)
    serializer_class = serializers.GatewaySerializer

    def get_queryset(self):
        queryset = Domain.get_gateway_queryset()
        return queryset


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    rbac_perms = {
        'POST': 'assets.test_gateway'
    }

    def get_queryset(self):
        queryset = Domain.get_gateway_queryset()
        return queryset

    def post(self, request, *args, **kwargs):
        gateway = self.get_object()
        local_port = self.request.data.get('port') or gateway.port
        try:
            local_port = int(local_port)
        except ValueError:
            raise ValidationError({'port': _('Number required')})
        ok, e = gateway.test_connective(local_port=local_port)
        if ok:
            return Response("ok")
        else:
            return Response({"error": e}, status=400)
