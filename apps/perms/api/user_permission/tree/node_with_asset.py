import abc

from django.conf import settings
from django.db.models import F, Value, CharField
from django.utils.functional import cached_property
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from common.utils.http import is_true

from assets.api import SerializeToTreeNodeMixin
from assets.models import Asset
from assets.pagination import NodeTreeCursorPagination
from common.utils import get_object_or_none, lazyproperty
from common.utils.common import timeit
from perms import serializers
from perms.hands import Node
from perms.models import PermNode
from perms.utils import UserPermAssetUtil
from perms.utils import UserPermNodeUtil
from ..mixin import SelfOrPKUserMixin

__all__ = [
    'UserPermedNodesWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsCategoryTreeApi',
]


class BaseUserNodeWithAssetAsTreeApi(
    SelfOrPKUserMixin, SerializeToTreeNodeMixin, ListAPIView
):
    page_limit = 10000
    default_include_asset_count = True

    def list(self, request, *args, **kwargs):
        offset = int(request.query_params.get('offset', 0))
        page_assets = self.get_page_assets()

        if not offset:
            nodes, assets = self.get_nodes_assets()
            include_asset_count = is_true(
                request.query_params.get(
                    'include_asset_count', self.default_include_asset_count
                )
            )
            page = page_assets[:self.page_limit]
            assets = [*assets, *page]
            tree_nodes = self.serialize_nodes(
                nodes, with_asset_amount=include_asset_count
            )
            tree_assets = self.serialize_assets(assets, **self.serialize_asset_kwargs)
            data = list(tree_nodes) + list(tree_assets)
        else:
            page = page_assets[offset:(offset + self.page_limit)]
            data = self.serialize_assets(page, **self.serialize_asset_kwargs) if page else []
        offset += len(page)
        headers = {'X-JMS-TREE-OFFSET': offset} if offset else {}
        return Response(data=data, headers=headers)

    @abc.abstractmethod
    def get_nodes_assets(self):
        return [], []

    def get_page_assets(self):
        return []

    @property
    def serialize_asset_kwargs(self):
        return {}


class UserPermedNodesWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    query_node_util: UserPermNodeUtil
    query_asset_util: UserPermAssetUtil

    def get_nodes_assets(self):
        self.query_node_util = UserPermNodeUtil(self.request.user)
        ung_nodes, ung_assets = self._get_nodes_assets_for_ungrouped()
        fav_nodes, fav_assets = self._get_nodes_assets_for_favorite()
        all_nodes, all_assets = self._get_nodes_assets_for_all()
        nodes = list(ung_nodes) + list(fav_nodes) + list(all_nodes)
        assets = list(ung_assets) + list(fav_assets) + list(all_assets)
        return nodes, assets

    def get_page_assets(self):
        return self.query_asset_util.get_all_assets().annotate(parent_key=F('nodes__key'))

    @timeit
    def _get_nodes_assets_for_ungrouped(self):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return [], []
        node = self.query_node_util.get_ungrouped_node()
        assets = self.query_asset_util.get_ungroup_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField()))
        return [node], assets

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)

    @timeit
    def _get_nodes_assets_for_favorite(self):
        node = self.query_node_util.get_favorite_node()
        assets = self.query_asset_util.get_favorite_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField()))
        return [node], assets

    @timeit
    def _get_nodes_assets_for_all(self):
        nodes = self.query_node_util.get_whole_tree_nodes(with_special=False)
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets = self.query_asset_util.get_perm_nodes_assets()
        else:
            assets = Asset.objects.none()
        assets = assets.annotate(parent_key=F('nodes__key'))
        return nodes, assets


class UserPermedNodeChildrenWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    """ 用户授权的节点的子节点与资产树 """

    @cached_property
    def tree_query(self):
        serializer = serializers.UserAuthorizationTreeQuerySerializer(
            data=self.request.query_params
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)

    @lazyproperty
    def query_node_util(self):
        return UserPermNodeUtil(self.user, asset_util=self.query_asset_util)

    def get_nodes(self):
        if not self.tree_query['include_nodes']:
            return [], None
        if not self.query_node_key:
            nodes = self.query_node_util.get_root_nodes(
                with_asset_count=False,
                include_favorites=self.include_favorites,
            )
            return nodes, None
        nodes = self.query_node_util.get_node_children(self.query_node_key)
        return nodes, self.paginate_nodes(nodes)

    def paginate_nodes(self, nodes):
        requested = (
            'node_page_size' in self.tree_query or
            'node_cursor' in self.request.query_params
        )
        if not requested or isinstance(nodes, list):
            return None
        paginator = NodeTreeCursorPagination()
        paginator.page_size_query_param = 'node_page_size'
        return paginator

    def get_assets(self):
        if not self.tree_query['include_assets']:
            return Asset.objects.none()
        key = self.query_node_key
        if not key:
            return Asset.objects.none()
        if key == PermNode.UNGROUPED_NODE_KEY:
            return self.query_asset_util.get_ungroup_assets()
        if key == PermNode.FAVORITE_NODE_KEY:
            if not self.include_favorites:
                return Asset.objects.none()
            return self.query_asset_util.get_favorite_assets()
        return self.query_asset_util.get_node_assets(key)

    @staticmethod
    def _ordered_assets(assets, order):
        if order == 'address':
            return assets.order_by('address', 'name', 'id')
        return assets.order_by('name', 'address', 'id')

    def list(self, request, *args, **kwargs):
        nodes, node_paginator = self.get_nodes()
        if node_paginator is not None:
            nodes = node_paginator.paginate_queryset(
                nodes, request, view=self
            )
        nodes = list(nodes)
        tree_nodes = self.serialize_nodes(
            nodes, with_asset_amount=False, with_has_children=False
        )
        for item, node in zip(tree_nodes, nodes):
            is_org_root = node.is_org_root()
            item['open'] = is_org_root
            item['meta']['data']['is_root'] = is_org_root

        assets = self._ordered_assets(
            self.get_assets(), self.tree_query['asset_order_by']
        )
        asset_page_size = self.tree_query.get('asset_page_size')
        asset_offset = self.tree_query['asset_offset']
        assets_truncated = False
        if asset_page_size is not None:
            assets = list(assets[
                asset_offset:asset_offset + asset_page_size + 1
            ])
            assets_truncated = len(assets) > asset_page_size
            assets = assets[:asset_page_size]
        tree_assets = self.serialize_assets(
            assets, node_key=self.query_node_key
        )
        results = [*tree_nodes, *tree_assets]

        paginated = (
            node_paginator is not None or
            asset_page_size is not None or
            'node_page_size' in self.tree_query
        )
        if not paginated:
            return Response(results)

        next_node_link = (
            node_paginator.get_next_link()
            if node_paginator is not None else None
        )
        parent_key = self.query_node_key or ''
        data = {
            'results': results,
            'node_pagination': {
                'has_more': bool(next_node_link),
                'limit': self.tree_query.get('node_page_size'),
                'next': next_node_link,
                'parent_key': parent_key,
            },
        }
        if asset_page_size is not None:
            data.update({
                'assets_truncated': assets_truncated,
                'assets_limit': asset_page_size,
                'asset_pagination': {
                    'has_more': assets_truncated,
                    'limit': asset_page_size,
                    'next_offset': (
                        asset_offset + len(tree_assets)
                        if assets_truncated else None
                    ),
                    'offset': asset_offset,
                    'parent_key': parent_key,
                },
            })
        return Response(data)

    @property
    def include_favorites(self):
        return self.tree_query['include_favorites']

    @lazyproperty
    def query_node_key(self):
        node_key = (
            self.request.query_params.get('parent_key') or
            self.request.query_params.get('key')
        )
        if node_key is None:
            node_id = self.request.query_params.get('id', None)
            node = get_object_or_none(Node, id=node_id)
            node_key = getattr(node, 'key', None)
        return node_key

    @property
    def serialize_asset_kwargs(self):
        return {
            'node_key': self.query_node_key
        }


class UserPermedNodeChildrenWithAssetsAsCategoryTreeApi(BaseUserNodeWithAssetAsTreeApi):
    @cached_property
    def pagination_query(self):
        serializer = serializers.UserAuthorizationTreeQuerySerializer(
            data=self.request.query_params
        )
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    @property
    def is_sync(self):
        sync = self.request.query_params.get('sync', 0)
        return int(sync) == 1

    @property
    def tp(self):
        params = self.request.query_params
        return [params.get('category'), params.get('type')]

    @lazyproperty
    def query_asset_util(self):
        return UserPermAssetUtil(self.user)

    @timeit
    def get_assets(self):
        return self.query_asset_util.get_all_assets()

    def _get_tree_nodes_async(self):
        if self.request.query_params.get('lv') == '0':
            return [], []
        if not self.tp or not all(self.tp):
            nodes = UserPermAssetUtil.get_type_nodes_tree_or_cached(self.user)
            if self.request.query_params.get('count_resource'):
                # 解决在 lina 使用该 api 类型树套娃问题
                for node in nodes:
                    if node.get('meta'):
                        node['isParent'] = False
            return nodes, []

        category, tp = self.tp
        assets = self.get_assets().filter(platform__type=tp, platform__category=category)
        return [], assets

    def _get_tree_nodes_sync(self):
        if self.request.query_params.get('lv'):
            return []
        nodes = self.query_asset_util.get_type_nodes_tree()
        return nodes, []

    @property
    def serialize_asset_kwargs(self):
        return {
            'get_pid': lambda asset, platform: 'ROOT_{}_{}'.format(platform.category.upper(), platform.type),
        }

    def serialize_nodes(self, nodes, with_asset_amount=False):
        return nodes

    def get_nodes_assets(self):
        if self.is_sync:
            return self._get_tree_nodes_sync()
        else:
            return self._get_tree_nodes_async()

    def get_page_assets(self):
        if self.is_sync:
            return self.get_assets()
        else:
            return []

    def list(self, request, *args, **kwargs):
        paginated = (
            not self.is_sync and
            all(self.tp) and
            'asset_page_size' in request.query_params
        )
        if not paginated:
            return super().list(request, *args, **kwargs)

        category, tp = self.tp
        page_size = self.pagination_query['asset_page_size']
        offset = self.pagination_query['asset_offset']
        assets = self.get_assets().filter(
            platform__type=tp, platform__category=category
        )
        if self.pagination_query['asset_order_by'] == 'address':
            assets = assets.order_by('address', 'name', 'id')
        else:
            assets = assets.order_by('name', 'address', 'id')
        page = list(assets[offset:offset + page_size + 1])
        has_more = len(page) > page_size
        page = page[:page_size]
        results = self.serialize_assets(page, **self.serialize_asset_kwargs)
        return Response({
            'results': results,
            'assets_truncated': has_more,
            'assets_limit': page_size,
            'asset_pagination': {
                'has_more': has_more,
                'limit': page_size,
                'next_offset': offset + len(page) if has_more else None,
                'offset': offset,
            },
        })
