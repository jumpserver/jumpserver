import abc

from django.conf import settings
from django.db.models import FilteredRelation, Q
from rest_framework.generics import ListAPIView, RetrieveAPIView

from assets.models import Asset, Node, MyAsset
from common.api.mixin import ExtraFilterFieldsMixin
from common.utils import get_logger, lazyproperty, is_uuid
from orgs.utils import tmp_to_root_org
from perms import serializers
from perms.filters import PermedAssetFilterSet
from perms.pagination import NodePermedAssetPagination, AllPermedAssetPagination
from perms.utils import UserPermAssetUtil, PermAssetDetailUtil
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
    search_fields = (
        'name', 'address', 'comment',
        'user_custom__name', 'user_custom__comment',
    )
    ordering_fields = ("name", "address", "connectivity", "date_updated")
    filterset_class = PermedAssetFilterSet
    serializer_class = serializers.AssetPermedSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        if settings.ASSET_SIZE == 'small':
            self.ordering = ['name']
        assets = self.get_assets()
        custom_user_id = self.user.id if self.need_custom_value_user else None
        assets = assets.alias(
            user_custom=FilteredRelation(
                'my_assets',
                condition=Q(my_assets__user_id=custom_user_id),
            )
        )
        assets = self.serializer_class.setup_eager_loading(assets)
        return assets

    def get_serializer(self, *args, **kwargs):
        if len(args) == 1 and kwargs.get('many', False) and self.need_custom_value_user:
            MyAsset.set_asset_custom_value(args[0], self.user)
        return super().get_serializer(*args, **kwargs)

    @lazyproperty
    def need_custom_value_user(self):
        return self.request_user_is_self() or self.request.user.is_service_account

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
        if self.user.is_superuser and self.request.query_params.get('id'):
            return Asset.objects.filter(id=self.request.query_params.get('id'))

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
