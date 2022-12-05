from django.conf import settings
from rest_framework.generics import ListAPIView

from assets.models import Asset, Node
from common.utils import get_logger
from perms import serializers
from perms.pagination import AllGrantedAssetPagination
from perms.pagination import NodeGrantedAssetPagination
from perms.utils.user_permission import UserGrantedAssetsQueryUtils
from .mixin import (
    SelfOrPKUserMixin, RebuildTreeMixin,
    PermedAssetSerializerMixin, AssetsTreeFormatMixin
)

__all__ = [
    'UserDirectPermedAssetsApi',
    'UserFavoriteAssetsApi',
    'UserDirectPermedAssetsAsTreeApi',
    'UserUngroupAssetsAsTreeApi',
    'UserAllPermedAssetsApi',
    'UserPermedNodeAssetsApi',
]

logger = get_logger(__name__)


class UserDirectPermedAssetsApi(SelfOrPKUserMixin, PermedAssetSerializerMixin, ListAPIView):
    """ 直接授权给用户的资产 """
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()

        assets = UserGrantedAssetsQueryUtils(self.user) \
            .get_direct_granted_assets() \
            .prefetch_related('platform') \
            .only(*self.only_fields)
        return assets


class UserFavoriteAssetsApi(SelfOrPKUserMixin, PermedAssetSerializerMixin, ListAPIView):
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    """ 用户收藏的授权资产 """

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()

        user = self.user
        utils = UserGrantedAssetsQueryUtils(user)
        assets = utils.get_favorite_assets()
        assets = assets.prefetch_related('platform').only(*self.only_fields)
        return assets


class UserDirectPermedAssetsAsTreeApi(RebuildTreeMixin, AssetsTreeFormatMixin, UserDirectPermedAssetsApi):
    """ 用户直接授权的资产作为树 """
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()

        assets = UserGrantedAssetsQueryUtils(self.user) \
            .get_direct_granted_assets() \
            .prefetch_related('platform') \
            .only(*self.only_fields)
        return assets


class UserUngroupAssetsAsTreeApi(UserDirectPermedAssetsAsTreeApi):
    """ 用户未分组节点下的资产作为树 """

    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllPermedAssetsApi(SelfOrPKUserMixin, PermedAssetSerializerMixin, ListAPIView):
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = AllGrantedAssetPagination

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        queryset = UserGrantedAssetsQueryUtils(self.user).get_all_granted_assets()
        only_fields = [i for i in self.only_fields if i not in ['protocols']]
        queryset = queryset.prefetch_related('platform', 'protocols').only(*only_fields)
        return queryset


class UserPermedNodeAssetsApi(SelfOrPKUserMixin, PermedAssetSerializerMixin, ListAPIView):
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = NodeGrantedAssetPagination
    kwargs: dict
    pagination_node: Node

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        node_id = self.kwargs.get("node_id")

        node, assets = UserGrantedAssetsQueryUtils(self.user).get_node_all_assets(node_id)
        assets = assets.prefetch_related('platform').only(*self.only_fields)
        self.pagination_node = node
        return assets
