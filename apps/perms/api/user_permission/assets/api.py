from rest_framework.generics import ListAPIView
from django.conf import settings

from common.utils import get_logger
from ..mixin import AssetRoleAdminMixin, AssetRoleUserMixin
from .mixin import (
    UserAllGrantedAssetsQuerysetMixin, UserDirectGrantedAssetsQuerysetMixin, UserFavoriteGrantedAssetsMixin,
    UserGrantedNodeAssetsMixin, AssetsSerializerFormatMixin, AssetsTreeFormatMixin,
)

__all__ = [
    'UserDirectGrantedAssetsApi', 'MyDirectGrantedAssetsApi',
    'UserFavoriteGrantedAssetsApi',
    'MyFavoriteGrantedAssetsApi', 'UserDirectGrantedAssetsAsTreeApi',
    'MyUngroupAssetsAsTreeApi',
    'UserAllGrantedAssetsApi', 'MyAllGrantedAssetsApi', 'MyAllAssetsAsTreeApi',
    'UserGrantedNodeAssetsApi', 'MyGrantedNodeAssetsApi',
]

logger = get_logger(__name__)


class UserDirectGrantedAssetsApi(
    AssetRoleAdminMixin, UserDirectGrantedAssetsQuerysetMixin,
    AssetsSerializerFormatMixin, ListAPIView
):
    """ 直接授权给用户的资产 """
    pass


class MyDirectGrantedAssetsApi(AssetRoleUserMixin, UserDirectGrantedAssetsApi):
    """ 直接授权给我的资产 """
    pass


class UserFavoriteGrantedAssetsApi(
    AssetRoleAdminMixin, UserFavoriteGrantedAssetsMixin,
    AssetsSerializerFormatMixin, ListAPIView
):
    """ 用户收藏的授权资产 """
    pass


class MyFavoriteGrantedAssetsApi(AssetRoleUserMixin, UserFavoriteGrantedAssetsApi):
    """ 我收藏的授权资产 """
    pass


class UserDirectGrantedAssetsAsTreeApi(AssetsTreeFormatMixin, UserDirectGrantedAssetsApi):
    """ 用户直接授权的资产作为树 """
    pass


class MyUngroupAssetsAsTreeApi(AssetRoleUserMixin, UserDirectGrantedAssetsAsTreeApi):
    """ 我的未分组节点下的资产作为树 """

    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllGrantedAssetsApi(
    AssetRoleAdminMixin, UserAllGrantedAssetsQuerysetMixin,
    AssetsSerializerFormatMixin, ListAPIView
):
    """ 授权给用户的所有资产 """
    pass


class MyAllGrantedAssetsApi(AssetRoleUserMixin, UserAllGrantedAssetsApi):
    """ 授权给我的所有资产 """
    pass


class MyAllAssetsAsTreeApi(AssetsTreeFormatMixin, MyAllGrantedAssetsApi):
    """ 授权给我的所有资产作为树 """
    pass


class UserGrantedNodeAssetsApi(
    AssetRoleAdminMixin, UserGrantedNodeAssetsMixin,
    AssetsSerializerFormatMixin, ListAPIView
):
    """ 授权给用户的节点资产 """
    pass


class MyGrantedNodeAssetsApi(AssetRoleUserMixin, UserGrantedNodeAssetsApi):
    """ 授权给我的节点资产 """
    pass
