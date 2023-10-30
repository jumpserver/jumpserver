import abc
import re
from collections import defaultdict
from urllib.parse import parse_qsl

from django.conf import settings
from django.db.models import F, Value, CharField
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.generics import ListAPIView
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.response import Response

from accounts.const import AliasAccount
from assets.api import SerializeToTreeNodeMixin
from assets.const import AllTypes
from assets.models import Asset
from assets.utils import KubernetesTree
from authentication.models import ConnectionToken
from common.utils import get_object_or_none, lazyproperty
from common.utils.common import timeit
from perms.hands import Node
from perms.models import PermNode
from perms.utils import PermAssetDetailUtil, UserPermNodeUtil
from perms.utils import UserPermAssetUtil
from .mixin import RebuildTreeMixin
from ..mixin import SelfOrPKUserMixin

__all__ = [
    'UserGrantedK8sAsTreeApi',
    'UserPermedNodesWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsTreeApi',
    'UserPermedNodeChildrenWithAssetsAsCategoryTreeApi',
]


class BaseUserNodeWithAssetAsTreeApi(
    SelfOrPKUserMixin, RebuildTreeMixin,
    SerializeToTreeNodeMixin, ListAPIView
):

    def list(self, request, *args, **kwargs):
        nodes, assets = self.get_nodes_assets()
        tree_nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        tree_assets = self.serialize_assets(assets, node_key=self.node_key_for_serialize_assets)
        data = list(tree_nodes) + list(tree_assets)
        return Response(data=data)

    @abc.abstractmethod
    def get_nodes_assets(self):
        return [], []

    @lazyproperty
    def node_key_for_serialize_assets(self):
        return None


class UserPermedNodesWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    query_node_util: UserPermNodeUtil
    query_asset_util: UserPermAssetUtil

    def get_nodes_assets(self):
        self.query_node_util = UserPermNodeUtil(self.request.user)
        self.query_asset_util = UserPermAssetUtil(self.request.user)
        ung_nodes, ung_assets = self._get_nodes_assets_for_ungrouped()
        fav_nodes, fav_assets = self._get_nodes_assets_for_favorite()
        all_nodes, all_assets = self._get_nodes_assets_for_all()
        nodes = list(ung_nodes) + list(fav_nodes) + list(all_nodes)
        assets = list(ung_assets) + list(fav_assets) + list(all_assets)
        return nodes, assets

    @timeit
    def _get_nodes_assets_for_ungrouped(self):
        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            return [], []
        node = self.query_node_util.get_ungrouped_node()
        assets = self.query_asset_util.get_ungroup_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField())) \
            .prefetch_related('platform')
        return [node], assets

    @timeit
    def _get_nodes_assets_for_favorite(self):
        node = self.query_node_util.get_favorite_node()
        assets = self.query_asset_util.get_favorite_assets()
        assets = assets.annotate(parent_key=Value(node.key, output_field=CharField())) \
            .prefetch_related('platform')
        return [node], assets

    def _get_nodes_assets_for_all(self):
        nodes = self.query_node_util.get_whole_tree_nodes(with_special=False)
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            assets = self.query_asset_util.get_perm_nodes_assets()
        else:
            assets = self.query_asset_util.get_all_assets()
        assets = assets.annotate(parent_key=F('nodes__key')).prefetch_related('platform')
        return nodes, assets


class UserPermedNodeChildrenWithAssetsAsTreeApi(BaseUserNodeWithAssetAsTreeApi):
    """ 用户授权的节点的子节点与资产树 """

    # 默认展开的节点key
    default_unfolded_node_key = None

    def get_nodes_assets(self):
        query_node_util = UserPermNodeUtil(self.user)
        query_asset_util = UserPermAssetUtil(self.user)
        node_key = self.query_node_key
        if not node_key:
            nodes, unfolded_node = query_node_util.get_top_level_nodes(with_unfolded_node=True)
            if unfolded_node:
                """ 默认展开的节点, 获取根节点下的资产 """
                assets = query_asset_util.get_node_assets(key=unfolded_node.key)
                self.default_unfolded_node_key = unfolded_node.key
            else:
                assets = Asset.objects.none()
        elif node_key == PermNode.UNGROUPED_NODE_KEY:
            nodes = PermNode.objects.none()
            assets = query_asset_util.get_ungroup_assets()
        elif node_key == PermNode.FAVORITE_NODE_KEY:
            nodes = PermNode.objects.none()
            assets = query_asset_util.get_favorite_assets()
        else:
            nodes = query_node_util.get_node_children(node_key)
            assets = query_asset_util.get_node_assets(key=node_key)
        assets = assets.prefetch_related('platform')
        return nodes, assets

    @lazyproperty
    def query_node_key(self):
        node_key = self.request.query_params.get('key', None)
        if node_key is None:
            node_id = self.request.query_params.get('id', None)
            node = get_object_or_none(Node, id=node_id)
            node_key = getattr(node, 'key', None)
        return node_key

    @lazyproperty
    def node_key_for_serialize_assets(self):
        return self.query_node_key or self.default_unfolded_node_key


class UserPermedNodeChildrenWithAssetsAsCategoryTreeApi(
    SelfOrPKUserMixin, SerializeToTreeNodeMixin, ListAPIView
):
    @property
    def is_sync(self):
        sync = self.request.query_params.get('sync', 0)
        return int(sync) == 1

    @property
    def tp(self):
        return self.request.query_params.get('type')

    def get_assets(self):
        query_asset_util = UserPermAssetUtil(self.user)
        node = PermNode.objects.filter(
            granted_node_rels__user=self.user, parent_key='').first()
        if node:
            __, assets = query_asset_util.get_node_all_assets(node.id)
        else:
            assets = Asset.objects.none()
        return assets

    def to_tree_nodes(self, assets):
        if not assets:
            return []
        assets = assets.annotate(tp=F('platform__type'))
        asset_type_map = defaultdict(list)
        for asset in assets:
            asset_type_map[asset.tp].append(asset)
        tp = self.tp
        if tp:
            assets = asset_type_map.get(tp, [])
            if not assets:
                return []
            pid = f'ROOT_{str(assets[0].category).upper()}_{tp}'
            return self.serialize_assets(assets, pid=pid)
        params = self.request.query_params
        get_root = not list(filter(lambda x: params.get(x), ('type', 'n')))
        resource_platforms = assets.order_by('id').values_list('platform_id', flat=True)
        node_all = AllTypes.get_tree_nodes(resource_platforms, get_root=get_root)
        pattern = re.compile(r'\(0\)?')
        nodes = []
        for node in node_all:
            meta = node.get('meta', {})
            if pattern.search(node['name']) or meta.get('type') == 'platform':
                continue
            _type = meta.get('_type')
            if _type:
                node['type'] = _type
            meta.setdefault('data', {})
            node['meta'] = meta
            nodes.append(node)

        if not self.is_sync:
            return nodes

        asset_nodes = []
        for node in nodes:
            node['open'] = True
            tp = node.get('meta', {}).get('_type')
            if not tp:
                continue
            assets = asset_type_map.get(tp, [])
            asset_nodes += self.serialize_assets(assets, pid=node['id'])
        return nodes + asset_nodes

    def list(self, request, *args, **kwargs):
        assets = self.get_assets()
        nodes = self.to_tree_nodes(assets)
        return Response(data=nodes)


class UserGrantedK8sAsTreeApi(SelfOrPKUserMixin, ListAPIView):
    """ 用户授权的K8s树 """

    def get_token(self):
        token_id = self.request.query_params.get('token')
        token = get_object_or_404(ConnectionToken, pk=token_id)
        if token.is_expired:
            raise PermissionDenied('Token is expired')
        token.renewal()
        return token

    def get_account_secret(self, token: ConnectionToken):
        util = PermAssetDetailUtil(self.user, token.asset)
        accounts = util.get_permed_accounts_for_user()
        account_name = token.account

        if account_name in [AliasAccount.INPUT, AliasAccount.USER]:
            return token.input_secret
        else:
            accounts = filter(lambda x: x.name == account_name, accounts)
            accounts = list(accounts)
            if not accounts:
                raise NotFound('Account is not found')
            account = accounts[0]
            return account.secret

    @staticmethod
    def get_namespace_and_pod(key):
        namespace_and_pod = dict(parse_qsl(key))
        pod = namespace_and_pod.get('pod')
        namespace = namespace_and_pod.get('namespace')
        return namespace, pod

    def list(self, request: Request, *args, **kwargs):
        token = self.get_token()
        asset = token.asset
        secret = self.get_account_secret(token)
        key = self.request.query_params.get('key')
        namespace, pod = self.get_namespace_and_pod(key)

        tree = []
        k8s_tree_instance = KubernetesTree(asset, secret)
        if not any([namespace, pod]) and not key:
            asset_node = k8s_tree_instance.as_asset_tree_node()
            tree.append(asset_node)
        tree.extend(k8s_tree_instance.async_tree_node(namespace, pod))
        return Response(data=tree)
