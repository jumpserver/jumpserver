from rest_framework.response import Response
from rest_framework.request import Request

from users.models import User
from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from perms.pagination import NodeGrantedAssetPagination, AllGrantedAssetPagination
from assets.models import Asset, Node
from perms import serializers
from perms.utils.asset.user_permission import UserGrantedAssetsQueryUtils, QuerySetStage

logger = get_logger(__name__)


# 获取数据的 ------------------------------------------------------------

class UserDirectGrantedAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    user: User

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        user = self.user
        assets = UserGrantedAssetsQueryUtils(user) \
            .get_direct_granted_assets() \
            .prefetch_related('platform') \
            .only(*self.only_fields)
        return assets


class UserAllGrantedAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = AllGrantedAssetPagination
    user: User

    def get_union_queryset(self, qs_stage: QuerySetStage):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        qs_stage.prefetch_related('platform').only(*self.only_fields)
        queryset = UserGrantedAssetsQueryUtils(self.user) \
            .get_all_granted_assets(qs_stage)
        return queryset


class UserFavoriteGrantedAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    user: User

    def get_union_queryset(self, qs_stage: QuerySetStage):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        user = self.user
        qs_stage.prefetch_related('platform').only(*self.only_fields)
        utils = UserGrantedAssetsQueryUtils(user)
        assets = utils.get_favorite_assets(qs_stage=qs_stage)
        return assets


class UserGrantedNodeAssetsMixin:
    only_fields = serializers.AssetGrantedSerializer.Meta.only_fields
    pagination_class = NodeGrantedAssetPagination
    pagination_node: Node
    user: User

    def get_union_queryset(self, qs_stage: QuerySetStage):
        if getattr(self, 'swagger_fake_view', False):
            return Asset.objects.none()
        node_id = self.kwargs.get("node_id")
        qs_stage.prefetch_related('platform').only(*self.only_fields)
        node, assets = UserGrantedAssetsQueryUtils(self.user).get_node_all_assets(
            node_id, qs_stage=qs_stage
        )
        self.pagination_node = node
        return assets


# 控制格式的 ----------------------------------------------------

class AssetsUnionQueryMixin:
    def get_queryset_union_prefer(self):
        if hasattr(self, 'get_union_queryset'):
            # 为了支持 union 查询
            queryset = Asset.objects.all().distinct()
            queryset = self.filter_queryset(queryset)
            qs_stage = QuerySetStage()
            qs_stage.and_with_queryset(queryset)
            queryset = self.get_union_queryset(qs_stage)
        else:
            queryset = self.filter_queryset(self.get_queryset())
        return queryset


class AssetsSerializerFormatMixin(AssetsUnionQueryMixin):
    """
    用户直接授权的资产的列表，也就是授权规则上直接授权的资产，并非是来自节点的
    """
    serializer_class = serializers.AssetGrantedSerializer
    filterset_fields = ['hostname', 'ip', 'id', 'comment']
    search_fields = ['hostname', 'ip', 'comment']

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset_union_prefer()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AssetsTreeFormatMixin(AssetsUnionQueryMixin, SerializeToTreeNodeMixin):
    """
    将 资产 序列化成树的结构返回
    """

    def list(self, request: Request, *args, **kwargs):
        queryset = self.get_queryset_union_prefer()

        if request.query_params.get('search'):
            # 如果用户搜索的条件不精准，会导致返回大量的无意义数据。
            # 这里限制一下返回数据的最大条数
            queryset = queryset[:999]
        data = self.serialize_assets(queryset, None)
        return Response(data=data)

    # def get_serializer_class(self):
    #     return EmptySerializer
