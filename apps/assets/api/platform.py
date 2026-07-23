import os
import shutil

from django.core.files.storage import default_storage
from django.db.models import Subquery, OuterRef, Count, Value
from django.db.models.functions import Coalesce
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from assets.const import AllTypes
from assets.models import Platform, Node, Asset, PlatformProtocol, PlatformAutomation
from assets.serializers import PlatformSerializer, PlatformProtocolSerializer, PlatformListSerializer
from assets.utils.platform_package import locate_package_root, save_platform_from_package, validate_platform_package
from common.api import JMSModelViewSet
from common.permissions import IsValidUser
from common.serializers import GroupedChoiceSerializer, FileSerializer
from common.utils.zip import safe_extract_zip
from rbac.models import RoleBinding

__all__ = ['AssetPlatformViewSet', 'PlatformAutomationMethodsApi', 'PlatformProtocolViewSet']




class PlatformFilter(filters.FilterSet):
    name__startswith = filters.CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Platform
        fields = ['name', 'category', 'type']


class AssetPlatformViewSet(JMSModelViewSet):
    queryset = Platform.objects.all()
    serializer_classes = {
        'default': PlatformSerializer,
        'list': PlatformListSerializer,
        'categories': GroupedChoiceSerializer,
        'upload': FileSerializer,
    }
    filterset_class = PlatformFilter
    search_fields = ['name']
    ordering = ['-internal', 'name']
    rbac_perms = {
        'categories': 'assets.view_platform',
        'type_constraints': 'assets.view_platform',
        'ops_methods': 'assets.view_platform',
        'filter_nodes_assets': 'assets.view_platform',
        'upload': 'assets.add_platform',
    }
    page_no_limit = True

    def get_queryset(self):
        # 因为没有走分页逻辑，所以需要这里 prefetch
        asset_count_subquery = (
            Asset.objects.filter(platform=OuterRef('pk'))
            .values('platform')
            .annotate(count=Count('id'))
            .values('count')
        )
        queryset = (
            super().get_queryset()
            .annotate(assets_amount=Coalesce(Subquery(asset_count_subquery), Value(0)))
            .prefetch_related('protocols', 'automation')
        )
        queryset = queryset.filter(type__in=AllTypes.get_types_values())
        return queryset

    def get_object(self):
        pk = self.kwargs.get('pk', '')
        if pk.isnumeric():
            return super().get_object()
        return self.get_queryset().get(name=pk)


    def check_permissions(self, request):
        if self.action == 'list' and RoleBinding.is_org_admin(request.user):
            return True
        else:
            return super().check_permissions(request)

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

    @action(methods=['post'], detail=False)
    def upload(self, request, *args, **kwargs):
        input_serializer = FileSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        file = input_serializer.validated_data['file']
        save_to = 'platforms/{}'.format(file.name + '.tmp.zip')
        if default_storage.exists(save_to):
            default_storage.delete(save_to)
        rel_path = default_storage.save(save_to, file)
        path = default_storage.path(rel_path)
        extract_to = default_storage.path('platforms/{}.tmp'.format(file.name))

        if os.path.exists(extract_to):
            shutil.rmtree(extract_to)

        try:
            safe_extract_zip(path, extract_to)
        except RuntimeError as e:
            raise ValidationError({'error': 'Invalid zip file: {}'.format(e)})

        tmp_dir = locate_package_root(extract_to, file.name, 'platform.yml')
        data = validate_platform_package(tmp_dir)
        if not data:
            raise ValidationError({'error': 'Missing platform.yml in package'})
        name = data['name']
        instance = Platform.objects.filter(name=name).first()
        platform = save_platform_from_package(
            tmp_dir, instance=instance, created_by='PlatformPackageUpload'
        )
        output_serializer = PlatformSerializer(platform, context=self.get_serializer_context())
        return Response(output_serializer.data, status=201)


class PlatformProtocolViewSet(JMSModelViewSet):
    queryset = PlatformProtocol.objects.all()
    serializer_class = PlatformProtocolSerializer
    filterset_fields = ['name', 'platform__name']
    rbac_perms = {
        '*': 'assets.add_platform'
    }


class PlatformAutomationMethodsApi(generics.ListAPIView):
    queryset = PlatformAutomation.objects.none()
    rbac_perms = {
        'list': 'assets.view_platform'
    }

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
