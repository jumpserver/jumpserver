# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView

from assets.models import Asset
from common.utils import get_logger
from orgs.mixins import generics
from perms.filters import AssetPermissionFilter
from perms.models import AssetPermission
from perms.serializers import AssetPermissionSerializer
from users.filters import UserFilter
from users.models import User, UserGroup
from users.serializers import UserSerializer, UserGroupSerializer

logger = get_logger(__file__)
__all__ = [
    'AssetPermUserListApi', 'AssetPermUserPermissionsListApi',
    'AssetPermUserGroupListApi', 'AssetPermUserGroupPermissionsListApi',
]


class BaseAssetPermUserOrUserGroupListApi(ListAPIView):
    rbac_perms = {
        'GET': 'perms.view_assetpermission'
    }

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
    rbac_perms = {
        'GET': 'perms.view_assetpermission'
    }

    def get_queryset(self):
        perms = self.get_asset_related_perms()
        users = User.get_queryset().filter(
            Q(assetpermissions__in=perms) | Q(groups__assetpermissions__in=perms)
        ).distinct()
        return users


class AssetPermUserGroupListApi(BaseAssetPermUserOrUserGroupListApi):
    serializer_class = UserGroupSerializer
    queryset = UserGroup.objects.none()

    def get_queryset(self):
        perms = self.get_asset_related_perms()
        user_groups = UserGroup.objects.filter(assetpermissions__in=perms).distinct()
        return user_groups


class BaseAssetRelatedPermissionListApi(generics.ListAPIView):
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


class AssetPermUserPermissionsListApi(BaseAssetRelatedPermissionListApi):
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


class AssetPermUserGroupPermissionsListApi(BaseAssetRelatedPermissionListApi):
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
