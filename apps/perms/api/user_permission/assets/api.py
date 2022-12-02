from django.conf import settings
from rest_framework.generics import ListAPIView

from common.utils import get_logger
from .mixin import (
    AssetsTreeFormatMixin,
    UserGrantedNodeAssetsMixin,
    AssetSerializerFormatMixin,
    UserFavoriteGrantedAssetsMixin,
    UserAllGrantedAssetsQuerysetMixin,
    UserDirectGrantedAssetsQuerysetMixin,
)
from ..mixin import SelfOrPKUserMixin, RebuildTreeMixin

__all__ = [
    'UserDirectGrantedAssetsApi',
    'UserFavoriteGrantedAssetsApi',
    'UserDirectGrantedAssetsAsTreeApi',
    'UserUngroupAssetsAsTreeApi',
    'UserAllGrantedAssetsApi',
    'UserGrantedNodeAssetsApi',
]

logger = get_logger(__name__)


class UserDirectGrantedAssetsApi(
    SelfOrPKUserMixin,
    UserDirectGrantedAssetsQuerysetMixin,
    AssetSerializerFormatMixin,
    ListAPIView
):
    """ 直接授权给用户的资产 """
    pass


class UserFavoriteGrantedAssetsApi(
    SelfOrPKUserMixin,
    UserFavoriteGrantedAssetsMixin,
    AssetSerializerFormatMixin,
    ListAPIView
):
    """ 用户收藏的授权资产 """
    pass


class UserDirectGrantedAssetsAsTreeApi(
    RebuildTreeMixin,
    AssetsTreeFormatMixin,
    UserDirectGrantedAssetsApi
):
    """ 用户直接授权的资产作为树 """
    pass


class UserUngroupAssetsAsTreeApi(UserDirectGrantedAssetsAsTreeApi):
    """ 用户未分组节点下的资产作为树 """
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllGrantedAssetsApi(
    SelfOrPKUserMixin,
    UserAllGrantedAssetsQuerysetMixin,
    AssetSerializerFormatMixin,
    ListAPIView
):
    """ 授权给用户的所有资产 """
    pass


class UserGrantedNodeAssetsApi(
    SelfOrPKUserMixin,
    UserGrantedNodeAssetsMixin,
    AssetSerializerFormatMixin,
    ListAPIView
):
    """ 授权给用户的节点资产 """
    pass
