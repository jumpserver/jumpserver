# ~*~ coding: utf-8 ~*~
from django.utils.translation import gettext as _
from django.views.generic.detail import SingleObjectMixin
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView, Response

from assets.tasks import test_gateways_connectivity_manual
from common.utils import get_logger
from orgs.mixins.api import OrgBulkModelViewSet
from .asset import HostViewSet
from .. import serializers
from ..models import Domain, Gateway

logger = get_logger(__file__)
__all__ = ['DomainViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class DomainViewSet(OrgBulkModelViewSet):
    model = Domain
    filterset_fields = ("name",)
    search_fields = filterset_fields
    ordering = ('name',)
    serializer_classes = {
        'default': serializers.DomainSerializer,
        'list': serializers.DomainListSerializer,
    }

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.DomainWithGatewaySerializer
        return super().get_serializer_class()


class GatewayViewSet(HostViewSet):
    perm_model = Gateway
    filterset_fields = ("domain__name", "name", "domain")
    search_fields = ("domain__name",)

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = serializers.GatewaySerializer
        return serializer_classes

    def get_queryset(self):
        queryset = Domain.get_gateway_queryset()
        return queryset


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    rbac_perms = {
        'POST': 'assets.test_assetconnectivity'
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
        task = test_gateways_connectivity_manual([gateway.id], local_port)
        return Response({'task': task.id})
