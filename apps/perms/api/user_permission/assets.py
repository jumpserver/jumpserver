import abc

from django.conf import settings
from rest_framework.generics import ListAPIView, RetrieveAPIView

from assets.api.asset.asset import AssetFilterSet
from assets.models import Asset, Node, MyAsset
from common.api.mixin import ExtraFilterFieldsMixin
from common.utils import get_logger, lazyproperty, is_uuid
from common.utils.django import get_object_or_none
from orgs.utils import tmp_to_root_org
from perms import serializers
from perms.pagination import NodePermedAssetPagination, AllPermedAssetPagination
from perms.utils import UserPermAssetUtil, PermAssetDetailUtil
from perms.utils.utils import UserPermUtil
from perms.tree import PermTreeNode
from .mixin import (
    SelfOrPKUserMixin
)

__all__ = [
    'UserAllPermedAssetsApi',
    'UserDirectPermedAssetsApi',
    'UserFavoriteAssetsApi',
    'UserPermedNodeAssetsApi',
    'UserPermedAssetRetrieveApi',
]

logger = get_logger(__name__)


class UserPermedAssetRetrieveApi(SelfOrPKUserMixin, RetrieveAPIView):
    serializer_class = serializers.AssetPermedDetailSerializer

    def get_object(self):
        with tmp_to_root_org():
            asset_id = self.kwargs.get('pk')
            util = PermAssetDetailUtil(self.user, asset_id)
            asset = util.asset
            asset.permed_accounts = util.get_permed_accounts_for_user()
            asset.permed_protocols = util.get_permed_protocols_for_user()
            return asset


class BaseUserPermedAssetsApi(SelfOrPKUserMixin, ExtraFilterFieldsMixin, ListAPIView):
    ordering = []
    search_fields = ('name', 'address', 'comment')
    ordering_fields = ("name", "address", "connectivity", "date_updated")
    filterset_class = AssetFilterSet
    serializer_class = serializers.AssetPermedSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        if settings.ASSET_SIZE == 'small':
            self.ordering = ['name']
        assets = self.get_assets()
        assets = self.serializer_class.setup_eager_loading(assets)
        return assets

    def get_serializer(self, *args, **kwargs):
        need_custom_value_user = self.request_user_is_self() or self.request.user.is_service_account
        if len(args) == 1 and kwargs.get('many', False) and need_custom_value_user:
            MyAsset.set_asset_custom_value(args[0], self.user)
        return super().get_serializer(*args, **kwargs)

    @abc.abstractmethod
    def get_assets(self):
        return Asset.objects.none()

    @lazyproperty
    def _util(self):
        return UserPermUtil(user=self.user)


class UserAllPermedAssetsApi(BaseUserPermedAssetsApi):

    def get_assets(self):
        if self.user.is_superuser and self.request.query_params.get('id'):
            return Asset.objects.filter(id=self.request.query_params.get('id'))

        node_id = self.request.query_params.get('node_id')

        if node_id == PermTreeNode.SpecialKey.FAVORITE:
            return UserPermUtil.get_favorite_assets(user=self.user)

        if node_id == PermTreeNode.SpecialKey.UNGROUPED:
            return self._util.get_ungrouped_assets()

        node = get_object_or_none(Node, id=node_id)
        if node:
            assets = self._util.get_node_all_assets(node)
            return assets

        assets = UserPermUtil.get_all_assets(user=self.user)
        return assets


class UserDirectPermedAssetsApi(BaseUserPermedAssetsApi):

    def get_assets(self):
        assets = self._util.get_ungrouped_assets()
        return assets


class UserFavoriteAssetsApi(BaseUserPermedAssetsApi):

    def get_assets(self):
        assets = UserPermUtil.get_favorite_assets(user=self.user)
        return assets


class UserPermedNodeAssetsApi(BaseUserPermedAssetsApi):
    pagination_class = NodePermedAssetPagination
    pagination_node: Node

    def get_assets(self):
        node_id = self.kwargs.get("node_id")
        node, assets = self.query_asset_util.get_node_all_assets(node_id)
        self.pagination_node = node
        return assets
