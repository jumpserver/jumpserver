from rest_framework.generics import ListAPIView
from django.conf import settings

from common.utils import get_logger
from ..mixin import AssetRoleAdminMixin, AssetRoleUserMixin
from .mixin import (
    UserAllGrantedAssetsQuerysetMixin, UserDirectGrantedAssetsQuerysetMixin, UserFavoriteGrantedAssetsMixin,
    UserGrantedNodeAssetsMixin, AssetsSerializerFormatMixin, AssetsTreeFormatMixin,
)

__all__ = [
    'UserDirectGrantedAssetsForAdminApi', 'MyDirectGrantedAssetsApi', 'UserFavoriteGrantedAssetsForAdminApi',
    'MyFavoriteGrantedAssetsApi', 'UserDirectGrantedAssetsAsTreeForAdminApi', 'MyUngroupAssetsAsTreeApi',
    'UserAllGrantedAssetsApi', 'MyAllGrantedAssetsApi', 'MyAllAssetsAsTreeApi', 'UserGrantedNodeAssetsForAdminApi',
    'MyGrantedNodeAssetsApi',
]

logger = get_logger(__name__)


class UserDirectGrantedAssetsForAdminApi(UserDirectGrantedAssetsQuerysetMixin,
                                         AssetRoleAdminMixin,
                                         AssetsSerializerFormatMixin,
                                         ListAPIView):
    pass


class MyDirectGrantedAssetsApi(UserDirectGrantedAssetsQuerysetMixin,
                               AssetRoleUserMixin,
                               AssetsSerializerFormatMixin,
                               ListAPIView):
    pass


class UserFavoriteGrantedAssetsForAdminApi(UserFavoriteGrantedAssetsMixin,
                                           AssetRoleAdminMixin,
                                           AssetsSerializerFormatMixin,
                                           ListAPIView):
    pass


class MyFavoriteGrantedAssetsApi(UserFavoriteGrantedAssetsMixin,
                                 AssetRoleUserMixin,
                                 AssetsSerializerFormatMixin,
                                 ListAPIView):
    pass


class UserDirectGrantedAssetsAsTreeForAdminApi(UserDirectGrantedAssetsQuerysetMixin,
                                               AssetRoleAdminMixin,
                                               AssetsTreeFormatMixin,
                                               ListAPIView):
    pass


class MyUngroupAssetsAsTreeApi(UserDirectGrantedAssetsQuerysetMixin,
                               AssetRoleUserMixin,
                               AssetsTreeFormatMixin,
                               ListAPIView):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllGrantedAssetsApi(UserAllGrantedAssetsQuerysetMixin,
                              AssetRoleAdminMixin,
                              AssetsSerializerFormatMixin,
                              ListAPIView):
    pass


class MyAllGrantedAssetsApi(UserAllGrantedAssetsQuerysetMixin,
                            AssetRoleUserMixin,
                            AssetsSerializerFormatMixin,
                            ListAPIView):
    pass


class MyAllAssetsAsTreeApi(UserAllGrantedAssetsQuerysetMixin,
                           AssetRoleUserMixin,
                           AssetsTreeFormatMixin,
                           ListAPIView):
    pass


class UserGrantedNodeAssetsForAdminApi(AssetRoleAdminMixin,
                                       UserGrantedNodeAssetsMixin,
                                       AssetsSerializerFormatMixin,
                                       ListAPIView):
    pass


class MyGrantedNodeAssetsApi(AssetRoleUserMixin,
                             UserGrantedNodeAssetsMixin,
                             AssetsSerializerFormatMixin,
                             ListAPIView):
    pass
