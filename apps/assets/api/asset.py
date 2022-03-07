# -*- coding: utf-8 -*-
#
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveAPIView, ListAPIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from common.utils import get_logger, get_object_or_none
from common.mixins.api import SuggestionMixin
from users.models import User, UserGroup
from users.serializers import UserSerializer, UserGroupSerializer
from users.filters import UserFilter
from perms.models import AssetPermission
from perms.serializers import AssetPermissionSerializer
from perms.filters import AssetPermissionFilter
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from assets.api import FilterAssetByNodeMixin
from ..models import Asset, Node, Platform
from .. import serializers
from ..tasks import (
    update_assets_hardware_info_manual, test_assets_connectivity_manual,
    test_system_users_connectivity_a_asset, push_system_users_a_asset
)
from ..filters import FilterAssetByNodeFilterBackend, LabelFilterBackend, IpInFilterBackend

logger = get_logger(__file__)
__all__ = [
    'AssetViewSet', 'AssetPlatformRetrieveApi',
    'AssetGatewayListApi', 'AssetPlatformViewSet',
    'AssetTaskCreateApi', 'AssetsTaskCreateApi',
    'AssetPermUserListApi', 'AssetPermUserPermissionsListApi',
    'AssetPermUserGroupListApi', 'AssetPermUserGroupPermissionsListApi',
]


class AssetViewSet(SuggestionMixin, FilterAssetByNodeMixin, OrgBulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    model = Asset
    filterset_fields = {
        'hostname': ['exact'],
        'ip': ['exact'],
        'system_users__id': ['exact'],
        'platform__base': ['exact'],
        'is_active': ['exact'],
        'protocols': ['exact', 'icontains']
    }
    search_fields = ("hostname", "ip")
    ordering_fields = ("hostname", "ip", "port", "cpu_cores")
    ordering = ('hostname', )
    serializer_classes = {
        'default': serializers.AssetSerializer,
        'suggestion': serializers.MiniAssetSerializer
    }
    rbac_perms = {
        'match': 'assets.match_asset'
    }
    extra_filter_backends = [FilterAssetByNodeFilterBackend, LabelFilterBackend, IpInFilterBackend]

    def set_assets_node(self, assets):
        if not isinstance(assets, list):
            assets = [assets]
        node_id = self.request.query_params.get('node_id')
        if not node_id:
            return
        node = get_object_or_none(Node, pk=node_id)
        if not node:
            return
        node.assets.add(*assets)

    def perform_create(self, serializer):
        assets = serializer.save()
        self.set_assets_node(assets)


class AssetPlatformRetrieveApi(RetrieveAPIView):
    queryset = Platform.objects.all()
    serializer_class = serializers.PlatformSerializer
    rbac_perms = {
        'retrieve': 'assets.view_gateway'
    }

    def get_object(self):
        asset_pk = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_pk)
        return asset.platform


class AssetPlatformViewSet(ModelViewSet):
    queryset = Platform.objects.all()
    serializer_class = serializers.PlatformSerializer
    filterset_fields = ['name', 'base']
    search_fields = ['name']

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)


class AssetsTaskMixin:

    def perform_assets_task(self, serializer):
        data = serializer.validated_data
        action = data['action']
        assets = data.get('assets', [])
        if action == "refresh":
            task = update_assets_hardware_info_manual.delay(assets)
        else:
            # action == 'test':
            task = test_assets_connectivity_manual.delay(assets)
        return task

    def perform_create(self, serializer):
        task = self.perform_assets_task(serializer)
        self.set_task_to_serializer_data(serializer, task)

    def set_task_to_serializer_data(self, serializer, task):
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)


class AssetTaskCreateApi(AssetsTaskMixin, generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetTaskSerializer

    def create(self, request, *args, **kwargs):
        pk = self.kwargs.get('pk')
        request.data['asset'] = pk
        request.data['assets'] = [pk]
        return super().create(request, *args, **kwargs)

    def check_permissions(self, request):
        action = request.data.get('action')
        action_perm_require = {
            'refresh': 'assets.refresh_assethardwareinfo',
            'push_system_user': 'assets.push_assetsystemuser',
            'test': 'assets.test_assetconnectivity',
            'test_system_user': 'assets.test_assetconnectivity'
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    def perform_asset_task(self, serializer):
        data = serializer.validated_data
        action = data['action']
        if action not in ['push_system_user', 'test_system_user']:
            return

        asset = data['asset']
        system_users = data.get('system_users')
        if not system_users:
            system_users = asset.get_all_system_users()
        if action == 'push_system_user':
            task = push_system_users_a_asset.delay(system_users, asset=asset)
        elif action == 'test_system_user':
            task = test_system_users_connectivity_a_asset.delay(system_users, asset=asset)
        else:
            task = None
        return task

    def perform_create(self, serializer):
        task = self.perform_asset_task(serializer)
        if not task:
            task = self.perform_assets_task(serializer)
        self.set_task_to_serializer_data(serializer, task)


class AssetsTaskCreateApi(AssetsTaskMixin, generics.CreateAPIView):
    model = Asset
    serializer_class = serializers.AssetsTaskSerializer


class AssetGatewayListApi(generics.ListAPIView):
    serializer_class = serializers.GatewayWithAuthSerializer
    rbac_perms = {
        'list': 'assets.view_gateway'
    }

    def get_queryset(self):
        asset_id = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        if not asset.domain:
            return []
        queryset = asset.domain.gateways.filter(protocol='ssh')
        return queryset


class BaseAssetPermUserOrUserGroupListApi(ListAPIView):

    def get_object(self):
        asset_id = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        return asset

    def get_asset_related_perms(self):
        asset = self.get_object()
        nodes = asset.get_all_nodes(flat=True)
        perms = AssetPermission.objects.filter(Q(assets=asset) | Q(nodes__in=nodes))
        return perms


class AssetPermUserListApi(BaseAssetPermUserOrUserGroupListApi):
    filterset_class = UserFilter
    search_fields = ('username', 'email', 'name', 'id', 'source', 'role')
    serializer_class = UserSerializer

    def get_queryset(self):
        perms = self.get_asset_related_perms()
        users = User.objects.filter(
            Q(assetpermissions__in=perms) | Q(groups__assetpermissions__in=perms)
        ).distinct()
        return users


class AssetPermUserGroupListApi(BaseAssetPermUserOrUserGroupListApi):
    serializer_class = UserGroupSerializer

    def get_queryset(self):
        perms = self.get_asset_related_perms()
        user_groups = UserGroup.objects.filter(assetpermissions__in=perms).distinct()
        return user_groups


class BaseAssetPermUserOrUserGroupPermissionsListApiMixin(generics.ListAPIView):
    model = AssetPermission
    serializer_class = AssetPermissionSerializer
    filterset_class = AssetPermissionFilter
    search_fields = ('name',)
    rbac_perms = {
        'list': 'perms.view_assetpermission'
    }

    def get_object(self):
        asset_id = self.kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        return asset

    def filter_asset_related(self, queryset):
        asset = self.get_object()
        nodes = asset.get_all_nodes(flat=True)
        perms = queryset.filter(Q(assets=asset) | Q(nodes__in=nodes))
        return perms

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_asset_related(queryset)
        return queryset


class AssetPermUserPermissionsListApi(BaseAssetPermUserOrUserGroupPermissionsListApiMixin):
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_user_related(queryset)
        queryset = queryset.distinct()
        return queryset

    def filter_user_related(self, queryset):
        user = self.get_perm_user()
        user_groups = user.groups.all()
        perms = queryset.filter(Q(users=user) | Q(user_groups__in=user_groups))
        return perms

    def get_perm_user(self):
        user_id = self.kwargs.get('perm_user_id')
        user = get_object_or_404(User, pk=user_id)
        return user


class AssetPermUserGroupPermissionsListApi(BaseAssetPermUserOrUserGroupPermissionsListApiMixin):
    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_user_group_related(queryset)
        queryset = queryset.distinct()
        return queryset

    def filter_user_group_related(self, queryset):
        user_group = self.get_perm_user_group()
        perms = queryset.filter(user_groups=user_group)
        return perms

    def get_perm_user_group(self):
        user_group_id = self.kwargs.get('perm_user_group_id')
        user_group = get_object_or_404(UserGroup, pk=user_group_id)
        return user_group

