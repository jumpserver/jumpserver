# -*- coding: utf-8 -*-
#
from django.utils.decorators import method_decorator
from perms.api.user_permission.mixin import UserNodeGrantStatusDispatchMixin
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.conf import settings

from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from perms.pagination import GrantedAssetLimitOffsetPagination
from assets.models import Asset, Node, FavoriteAsset
from orgs.utils import tmp_to_root_org
from ... import serializers
from ...utils.user_asset_permission import (
    get_node_all_granted_assets, get_user_direct_granted_assets,
    get_user_granted_all_assets
)
from .mixin import ForAdminMixin, ForUserMixin


logger = get_logger(__name__)


@method_decorator(tmp_to_root_org(), name='list')
class UserDirectGrantedAssetsApi(ListAPIView):
    """
    用户直接授权的资产的列表，也就是授权规则上直接授权的资产，并非是来自节点的
    """
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_queryset(self):
        user = self.user
        assets = get_user_direct_granted_assets(user)\
            .prefetch_related('platform')\
            .only(*self.only_fields)
        return assets


@method_decorator(tmp_to_root_org(), name='list')
class UserFavoriteGrantedAssetsApi(ListAPIView):
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def get_queryset(self):
        user = self.user
        assets = FavoriteAsset.get_user_favorite_assets(user)\
            .prefetch_related('platform')\
            .only(*self.only_fields)
        return assets


@method_decorator(tmp_to_root_org(), name='list')
class AssetsAsTreeMixin(SerializeToTreeNodeMixin):
    """
    将 资产 序列化成树的结构返回
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        data = self.serialize_assets(queryset, None)
        return Response(data=data)


class UserDirectGrantedAssetsForAdminApi(ForAdminMixin, UserDirectGrantedAssetsApi):
    pass


class MyDirectGrantedAssetsApi(ForUserMixin, UserDirectGrantedAssetsApi):
    pass


class UserFavoriteGrantedAssetsForAdminApi(ForAdminMixin, UserFavoriteGrantedAssetsApi):
    pass


class MyFavoriteGrantedAssetsApi(ForUserMixin, UserFavoriteGrantedAssetsApi):
    pass


@method_decorator(tmp_to_root_org(), name='list')
class UserDirectGrantedAssetsAsTreeForAdminApi(ForAdminMixin, AssetsAsTreeMixin, UserDirectGrantedAssetsApi):
    pass


@method_decorator(tmp_to_root_org(), name='list')
class MyUngroupAssetsAsTreeApi(ForUserMixin, AssetsAsTreeMixin, UserDirectGrantedAssetsApi):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


@method_decorator(tmp_to_root_org(), name='list')
class UserAllGrantedAssetsApi(ListAPIView):
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields

    def get_queryset(self):
        queryset = get_user_granted_all_assets(self.user)
        queryset = queryset.prefetch_related('platform')
        return queryset.only(*self.only_fields)


class MyAllAssetsAsTreeApi(ForUserMixin, AssetsAsTreeMixin, UserAllGrantedAssetsApi):
    search_fields = ['hostname', 'ip']


@method_decorator(tmp_to_root_org(), name='list')
class UserGrantedNodeAssetsApi(UserNodeGrantStatusDispatchMixin, ListAPIView):
    serializer_class = serializers.AssetGrantedSerializer
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    filter_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']
    pagination_class = GrantedAssetLimitOffsetPagination
    pagination_node: Node

    def get_queryset(self):
        node_id = self.kwargs.get("node_id")
        node = Node.objects.get(id=node_id)
        self.pagination_node = node
        return self.dispatch_get_data(node.key, self.user)

    def get_data_on_node_direct_granted(self, key):
        # 如果这个节点是直接授权的(或者说祖先节点直接授权的), 获取下面的所有资产
        return Node.get_node_all_assets_by_key_v2(key)

    def get_data_on_node_indirect_granted(self, key):
        self.pagination_node = self.get_mapping_node_by_key(key, self.user)
        return get_node_all_granted_assets(self.user, key)

    def get_data_on_node_not_granted(self, key):
        return Asset.objects.none()


class UserGrantedNodeAssetsForAdminApi(ForAdminMixin, UserGrantedNodeAssetsApi):
    pass


class MyGrantedNodeAssetsApi(ForUserMixin, UserGrantedNodeAssetsApi):
    pass
