# ~*~ coding: utf-8 ~*~
from django.utils.translation import gettext as _, gettext_lazy
from django_filters import rest_framework as drf_filters
from django.views.generic.detail import SingleObjectMixin
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView, Response

from assets.tasks import test_gateways_connectivity_manual
from common.drf.filters import BaseFilterSet
from common.utils import get_logger
from orgs.mixins.api import OrgBulkModelViewSet
from .asset import HostViewSet
from .. import serializers
from ..models import Zone, Gateway

logger = get_logger(__file__)
__all__ = ['ZoneViewSet', 'GatewayViewSet', "GatewayTestConnectionApi"]


class GatewayFilterSet(BaseFilterSet):
    zone = drf_filters.UUIDFilter(
        field_name='zone_id', label=gettext_lazy('Zone ID')
    )
    zone__name = drf_filters.CharFilter(
        field_name='zone__name', label=gettext_lazy('Zone name')
    )

    class Meta:
        model = Gateway
        fields = (
            'id', 'name', 'address', 'connectivity', 'zone', 'zone__name',
        )


class ZoneViewSet(OrgBulkModelViewSet):
    model = Zone
    filterset_fields = ("name",)
    search_fields = filterset_fields
    serializer_classes = {
        'default': serializers.ZoneSerializer,
        'list': serializers.ZoneListSerializer,
    }

    def get_serializer_class(self):
        if self.request.query_params.get('gateway'):
            return serializers.ZoneWithGatewaySerializer
        return super().get_serializer_class()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class GatewayViewSet(HostViewSet):
    perm_model = Gateway
    filterset_class = GatewayFilterSet
    search_fields = ('name', 'address', 'zone__name')

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = serializers.GatewaySerializer
        return serializer_classes

    def get_queryset(self):
        queryset = Zone.get_gateway_queryset()
        return queryset


class GatewayTestConnectionApi(SingleObjectMixin, APIView):
    rbac_perms = {
        'POST': 'assets.test_assetconnectivity'
    }

    def get_queryset(self):
        queryset = Zone.get_gateway_queryset()
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
