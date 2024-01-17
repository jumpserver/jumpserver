from rest_framework import generics
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from assets.const import AllTypes
from assets.models import Platform, Node, Asset, PlatformProtocol
from assets.serializers import PlatformSerializer, PlatformProtocolSerializer
from common.api import JMSModelViewSet
from common.permissions import IsValidUser
from common.serializers import GroupedChoiceSerializer

__all__ = ['AssetPlatformViewSet', 'PlatformAutomationMethodsApi', 'PlatformProtocolViewSet']


class AssetPlatformViewSet(JMSModelViewSet):
    queryset = Platform.objects.all()
    serializer_classes = {
        'default': PlatformSerializer,
        'categories': GroupedChoiceSerializer,
    }
    filterset_fields = ['name', 'category', 'type']
    search_fields = ['name']
    rbac_perms = {
        'categories': 'assets.view_platform',
        'type_constraints': 'assets.view_platform',
        'ops_methods': 'assets.view_platform',
        'filter_nodes_assets': 'assets.view_platform',
    }

    def get_queryset(self):
        # 因为没有走分页逻辑，所以需要这里 prefetch
        queryset = super().get_queryset().prefetch_related(
            'protocols', 'automation', 'labels', 'labels__label',
        )
        queryset = queryset.filter(type__in=AllTypes.get_types_values())
        return queryset

    def get_object(self):
        pk = self.kwargs.get('pk', '')
        if pk.isnumeric():
            return super().get_object()
        return self.get_queryset().get(name=pk)

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)

    @action(methods=['post'], detail=False, url_path='filter-nodes-assets')
    def filter_nodes_assets(self, request, *args, **kwargs):
        node_ids = request.data.get('node_ids', [])
        asset_ids = set(request.data.get('asset_ids', []))
        platform_ids = set(request.data.get('platform_ids', []))

        if node_ids:
            nodes = Node.objects.filter(id__in=node_ids)
            node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
            asset_ids |= set(node_asset_ids)

        if asset_ids:
            _platform_ids = Asset.objects \
                .filter(id__in=set(asset_ids)) \
                .values_list('platform_id', flat=True)
            platform_ids |= set(_platform_ids)
        platforms = Platform.objects.filter(id__in=platform_ids)
        serializer = self.get_serializer(platforms, many=True)
        return Response(serializer.data)


class PlatformProtocolViewSet(JMSModelViewSet):
    queryset = PlatformProtocol.objects.all()
    serializer_class = PlatformProtocolSerializer
    filterset_fields = ['name', 'platform__name']
    rbac_perms = {
        '*': 'assets.add_platform'
    }


class PlatformAutomationMethodsApi(generics.ListAPIView):
    permission_classes = (IsValidUser,)

    @staticmethod
    def automation_methods():
        return AllTypes.get_automation_methods()

    def generate_serializer_fields(self):
        data = self.automation_methods()
        fields = {
            i['id']: i['params_serializer'](label=i['name'])
            if i['params_serializer'] else None
            for i in data
        }
        return fields

    def get_serializer_class(self):
        fields = self.generate_serializer_fields()
        serializer_name = 'AutomationMethodsSerializer'
        return type(serializer_name, (serializers.Serializer,), fields)

    def list(self, request, *args, **kwargs):
        data = self.generate_serializer_fields()
        serializer = self.get_serializer(data)
        return Response(serializer.data)
