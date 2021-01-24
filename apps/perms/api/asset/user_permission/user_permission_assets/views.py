from rest_framework.generics import ListAPIView
from django.conf import settings

from common.utils import get_logger
from ..mixin import ForAdminMixin, ForUserMixin
from .mixin import (
    UserAllGrantedAssetsMixin, UserDirectGrantedAssetsMixin, UserFavoriteGrantedAssetsMixin,
    UserGrantedNodeAssetsMixin, AssetsSerializerFormatMixin, AssetsTreeFormatMixin
)

__all__ = [
    'UserDirectGrantedAssetsForAdminApi', 'MyDirectGrantedAssetsApi', 'UserFavoriteGrantedAssetsForAdminApi',
    'MyFavoriteGrantedAssetsApi', 'UserDirectGrantedAssetsAsTreeForAdminApi', 'MyUngroupAssetsAsTreeApi',
    'UserAllGrantedAssetsApi', 'MyAllGrantedAssetsApi', 'MyAllAssetsAsTreeApi', 'UserGrantedNodeAssetsForAdminApi',
    'MyGrantedNodeAssetsApi',
]

logger = get_logger(__name__)


class UserDirectGrantedAssetsForAdminApi(UserDirectGrantedAssetsMixin,
                                         ForAdminMixin,
                                         AssetsSerializerFormatMixin,
                                         ListAPIView):
    pass


class MyDirectGrantedAssetsApi(UserDirectGrantedAssetsMixin,
                               ForUserMixin,
                               AssetsSerializerFormatMixin,
                               ListAPIView):
    pass


class UserFavoriteGrantedAssetsForAdminApi(UserFavoriteGrantedAssetsMixin,
                                           ForAdminMixin,
                                           AssetsSerializerFormatMixin,
                                           ListAPIView):
    pass


class MyFavoriteGrantedAssetsApi(UserFavoriteGrantedAssetsMixin,
                                 ForUserMixin,
                                 AssetsSerializerFormatMixin,
                                 ListAPIView):
    pass


class UserDirectGrantedAssetsAsTreeForAdminApi(UserDirectGrantedAssetsMixin,
                                               ForAdminMixin,
                                               AssetsTreeFormatMixin,
                                               ListAPIView):
    pass


class MyUngroupAssetsAsTreeApi(UserDirectGrantedAssetsMixin,
                               ForUserMixin,
                               AssetsTreeFormatMixin,
                               ListAPIView):
    def get_queryset(self):
        queryset = super().get_queryset()
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            queryset = queryset.none()
        return queryset


class UserAllGrantedAssetsApi(UserAllGrantedAssetsMixin,
                              ForAdminMixin,
                              AssetsSerializerFormatMixin,
                              ListAPIView):
    pass


class MyAllGrantedAssetsApi(UserAllGrantedAssetsMixin,
                            ForUserMixin,
                            AssetsSerializerFormatMixin,
                            ListAPIView):
    pass


class MyAllAssetsAsTreeApi(UserAllGrantedAssetsMixin,
                           ForUserMixin,
                           AssetsTreeFormatMixin,
                           ListAPIView):
    search_fields = ['hostname', 'ip']


class UserGrantedNodeAssetsForAdminApi(UserGrantedNodeAssetsMixin,
                                       ForAdminMixin,
                                       AssetsSerializerFormatMixin,
                                       ListAPIView):
    pass


class MyGrantedNodeAssetsApi(UserGrantedNodeAssetsMixin,
                             ForUserMixin,
                             AssetsTreeFormatMixin,
                             ListAPIView):
    pass
