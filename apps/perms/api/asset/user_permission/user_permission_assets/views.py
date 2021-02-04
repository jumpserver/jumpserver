from rest_framework.generics import ListAPIView
from django.conf import settings

from common.utils import get_logger
from ..mixin import RoleAdminMixin, RoleUserMixin
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
                                         RoleAdminMixin,
                                         AssetsSerializerFormatMixin,
                                         ListAPIView):
    pass


class MyDirectGrantedAssetsApi(UserDirectGrantedAssetsQuerysetMixin,
                               RoleUserMixin,
                               AssetsSerializerFormatMixin,
                               ListAPIView):
    pass


class UserFavoriteGrantedAssetsForAdminApi(UserFavoriteGrantedAssetsMixin,
                                           RoleAdminMixin,
                                           AssetsSerializerFormatMixin,
                                           ListAPIView):
    pass


class MyFavoriteGrantedAssetsApi(UserFavoriteGrantedAssetsMixin,
                                 RoleUserMixin,
                                 AssetsSerializerFormatMixin,
                                 ListAPIView):
    pass


class UserDirectGrantedAssetsAsTreeForAdminApi(UserDirectGrantedAssetsQuerysetMixin,
                                               RoleAdminMixin,
                                               AssetsTreeFormatMixin,
                                               ListAPIView):
    pass


class MyUngroupAssetsAsTreeApi(UserDirectGrantedAssetsQuerysetMixin,
                               RoleUserMixin,
                               AssetsTreeFormatMixin,
                               ListAPIView):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllGrantedAssetsApi(UserAllGrantedAssetsQuerysetMixin,
                              RoleAdminMixin,
                              AssetsSerializerFormatMixin,
                              ListAPIView):
    pass


class MyAllGrantedAssetsApi(UserAllGrantedAssetsQuerysetMixin,
                            RoleUserMixin,
                            AssetsSerializerFormatMixin,
                            ListAPIView):
    pass


class MyAllAssetsAsTreeApi(UserAllGrantedAssetsQuerysetMixin,
                           RoleUserMixin,
                           AssetsTreeFormatMixin,
                           ListAPIView):
    search_fields = ['hostname', 'ip']


class UserGrantedNodeAssetsForAdminApi(UserGrantedNodeAssetsMixin,
                                       RoleAdminMixin,
                                       AssetsSerializerFormatMixin,
                                       ListAPIView):
    pass


class MyGrantedNodeAssetsApi(UserGrantedNodeAssetsMixin,
                             RoleUserMixin,
                             AssetsSerializerFormatMixin,
                             ListAPIView):
    pass
