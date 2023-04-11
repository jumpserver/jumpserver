import abc

from rest_framework.generics import ListAPIView

from assets.api.asset.asset import AssetFilterSet
from assets.models import Asset, Node
from common.utils import get_logger, lazyproperty, is_uuid
from perms import serializers
from perms.pagination import AllPermedAssetPagination
from perms.pagination import NodePermedAssetPagination
from perms.utils import UserPermAssetUtil
from .mixin import (
    SelfOrPKUserMixin
)

__all__ = [
    'UserAllPermedAssetsApi',
    'UserDirectPermedAssetsApi',
    'UserFavoriteAssetsApi',
    'UserPermedNodeAssetsApi',
]

logger = get_logger(__name__)


class BaseUserPermedAssetsApi(SelfOrPKUserMixin, ListAPIView):
    ordering = ('name',)
    search_fields = ('name', 'address', 'comment')
    ordering_fields = ("name", "address")
    filterset_class = AssetFilterSet
    serializer_class = serializers.AssetPermedSerializer

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        if self.request.query_params.get('id'):
            serializer_class = serializers.AssetPermedDetailSerializer
        return serializer_class

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        assets = self.get_assets()
        assets = self.serializer_class.setup_eager_loading(assets)
        return assets

    @abc.abstractmethod
    def get_assets(self):
        return Asset.objects.none()

    query_asset_util: UserPermAssetUtil

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)


class UserAllPermedAssetsApi(BaseUserPermedAssetsApi):
    pagination_class = AllPermedAssetPagination

    def get_assets(self):
        node_id = self.request.query_params.get('node_id')
        if is_uuid(node_id):
            __, assets = self.query_asset_util.get_node_all_assets(node_id)
        else:
            assets = self.query_asset_util.get_all_assets()
        return assets


class UserDirectPermedAssetsApi(BaseUserPermedAssetsApi):
    def get_assets(self):
        return self.query_asset_util.get_direct_assets()


class UserFavoriteAssetsApi(BaseUserPermedAssetsApi):
    def get_assets(self):
        return self.query_asset_util.get_favorite_assets()


class UserPermedNodeAssetsApi(BaseUserPermedAssetsApi):
    pagination_class = NodePermedAssetPagination
    pagination_node: Node

    def get_assets(self):
        node_id = self.kwargs.get("node_id")
        node, assets = self.query_asset_util.get_node_all_assets(node_id)
        self.pagination_node = node
        return assets
