from rest_framework.request import Request
from rest_framework.response import Response

from assets.api.asset.asset import AssetFilterSet
from assets.api.mixin import SerializeToTreeNodeMixin
from assets.models import Asset, Node
from common.utils import get_logger
from perms import serializers
from perms.pagination import NodeGrantedAssetPagination, AllGrantedAssetPagination
from perms.utils.user_permission import UserGrantedAssetsQueryUtils
from users.models import User

logger = get_logger(__name__)


# 获取数据的 ------------------------------------------------------------

class UserDirectGrantedAssetsQuerysetMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    user: User

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        assets = UserGrantedAssetsQueryUtils(self.user) \
            .get_direct_granted_assets() \
            .prefetch_related('platform') \
            .only(*self.only_fields)
        return assets


class UserAllGrantedAssetsQuerysetMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = AllGrantedAssetPagination
    ordering_fields = ("name", "address")
    filterset_class = AssetFilterSet
    ordering = ('name',)

    user: User

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        queryset = UserGrantedAssetsQueryUtils(self.user).get_all_granted_assets()
        only_fields = [i for i in self.only_fields if i not in ['protocols']]
        queryset = queryset.prefetch_related('platform', 'protocols').only(*only_fields)
        return queryset


class UserFavoriteGrantedAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    user: User

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        user = self.user
        utils = UserGrantedAssetsQueryUtils(user)
        assets = utils.get_favorite_assets()
        assets = assets.prefetch_related('platform').only(*self.only_fields)
        return assets


class UserGrantedNodeAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = NodeGrantedAssetPagination
    pagination_node: Node
    user: User
    kwargs: dict

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        node_id = self.kwargs.get("node_id")

        node, assets = UserGrantedAssetsQueryUtils(self.user).get_node_all_assets(
            node_id
        )
        assets = assets.prefetch_related('platform').only(*self.only_fields)
        self.pagination_node = node
        return assets


# 控制格式的 ----------------------------------------------------


class AssetsSerializerFormatMixin:
    serializer_class = serializers.AssetGrantedSerializer
    filterset_fields = ['name', 'address', 'id', 'comment']
    search_fields = ['name', 'address', 'comment']


class AssetsTreeFormatMixin(SerializeToTreeNodeMixin):
    """
    将 资产 序列化成树的结构返回
    """
    filter_queryset: callable
    get_queryset: callable

    filterset_fields = ['name', 'address', 'id', 'comment']
    search_fields = ['name', 'address', 'comment']

    def list(self, request: Request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        if request.query_params.get('search'):
            # 如果用户搜索的条件不精准，会导致返回大量的无意义数据。
            # 这里限制一下返回数据的最大条数
            queryset = queryset[:999]
            queryset = sorted(queryset, key=lambda asset: asset.name)
        data = self.serialize_assets(queryset, None)
        return Response(data=data)
