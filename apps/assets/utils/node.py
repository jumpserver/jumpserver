# ~*~ coding: utf-8 ~*~
#
from collections import defaultdict

from django.db.models import Count, F, Q

from common.struct import Stack
from common.utils import dict_get_any, is_uuid, get_object_or_none, timeit
from common.utils.http import is_true
from ..models import Node


def is_query_node_all_assets(request):
    request = request
    query_all_arg = request.query_params.get('all', 'true')
    show_current_asset_arg = request.query_params.get('show_current_asset')
    if show_current_asset_arg is not None:
        return not is_true(show_current_asset_arg)
    return is_true(query_all_arg)


def get_node_from_request(request):
    node_id = dict_get_any(request.query_params, ['node', 'node_id'])
    if not node_id:
        return None

    if is_uuid(node_id):
        node = get_object_or_none(Node, id=node_id)
    else:
        node = get_object_or_none(Node, key=node_id)
    return node


def _count_assets_by_target_key(relations, target_keys):
    """Count distinct assets for target node subtrees in one relation pass."""
    assets_by_key = defaultdict(set)
    matches_by_node_key = {}

    for asset_id, node_key in relations:
        matched_keys = matches_by_node_key.get(node_key)
        if matched_keys is None:
            matched_keys = []
            key = node_key
            while key:
                if key in target_keys:
                    matched_keys.append(key)
                key = key.rpartition(':')[0]
            matches_by_node_key[node_key] = matched_keys

        for key in matched_keys:
            assets_by_key[key].add(asset_id)

    return {
        key: len(assets_by_key[key])
        for key in target_keys
    }


def get_nodes_realtime_assets_amount(nodes, include_descendants=True):
    """Return exact asset amounts for a bounded node collection.

    Descendant counts intentionally avoid a correlated subquery per node.
    Relevant M2M rows are read once per organization, then distinct assets are
    accumulated along the materialized node path. All query expressions used
    here are portable across PostgreSQL, MySQL and MariaDB.
    """
    from assets.models import Asset

    nodes = list(nodes)
    amounts = {node.id: 0 for node in nodes}
    if not nodes:
        return amounts

    relations = Asset.nodes.through.objects.order_by()
    if not include_descendants:
        rows = (
            relations.filter(node_id__in=amounts)
            .values('node_id')
            .annotate(amount=Count('asset_id', distinct=True))
        )
        amounts.update({row['node_id']: row['amount'] for row in rows})
        return amounts

    nodes_by_org = defaultdict(list)
    for node in nodes:
        nodes_by_org[node.org_id].append(node)

    for org_id, org_nodes in nodes_by_org.items():
        nodes_by_key = {node.key: node for node in org_nodes}
        target_keys = set(nodes_by_key)
        descendant_filter = Q()
        for root_key in Node.clean_children_keys(target_keys):
            descendant_filter |= (
                Q(node__key=root_key) |
                Q(node__key__startswith=f'{root_key}:')
            )

        org_relations = (
            relations.filter(node__org_id=org_id)
            .filter(descendant_filter)
            .values_list('asset_id', 'node__key')
        )
        amounts_by_key = _count_assets_by_target_key(
            org_relations.iterator(chunk_size=10000), target_keys
        )
        for key, node in nodes_by_key.items():
            amounts[node.id] = amounts_by_key[key]

    return amounts


def attach_nodes_realtime_assets_amount(nodes, include_descendants=True):
    nodes = list(nodes)
    amounts = get_nodes_realtime_assets_amount(
        nodes, include_descendants=include_descendants
    )
    for node in nodes:
        node.assets_amount_realtime = amounts[node.id]
    return nodes


class NodeAssetsInfo:
    __slots__ = ('key', 'assets_amount', 'assets')

    def __init__(self, key, assets_amount, assets):
        self.key = key
        self.assets_amount = assets_amount
        self.assets = assets

    def __str__(self):
        return self.key


class NodeAssetsUtil:
    def __init__(self, nodes, nodekey_assetsid_mapper):
        """
        :param nodes: 节点
        :param nodekey_assetsid_mapper:  节点直接资产id的映射 {"key1": set(), "key2": set()}
        """
        self.nodes = nodes
        # node_id --> set(asset_id1, asset_id2)
        self.nodekey_assetsid_mapper = nodekey_assetsid_mapper
        self.nodekey_assetsinfo_mapper = {}

    @timeit
    def generate(self):
        # 准备排序好的资产信息数据
        infos = []
        for node in self.nodes:
            assets = self.nodekey_assetsid_mapper.get(node.key, set())
            info = NodeAssetsInfo(key=node.key, assets_amount=0, assets=assets)
            infos.append(info)
        infos = sorted(infos, key=lambda i: [int(i) for i in i.key.split(':')])
        # 这个守卫需要添加一下，避免最后一个无法出栈
        guarder = NodeAssetsInfo(key='', assets_amount=0, assets=set())
        infos.append(guarder)

        stack = Stack()
        for info in infos:
            # 如果栈顶的不是这个节点的父祖节点，那么可以出栈了，可以计算资产数量了
            while stack.top and not info.key.startswith(f'{stack.top.key}:'):
                pop_info = stack.pop()
                pop_info.assets_amount = len(pop_info.assets)
                self.nodekey_assetsinfo_mapper[pop_info.key] = pop_info
                if not stack.top:
                    continue
                stack.top.assets.update(pop_info.assets)
            stack.push(info)

    def get_assets_by_key(self, key):
        info = self.nodekey_assetsinfo_mapper[key]
        return info['assets']

    def get_assets_amount(self, key):
        info = self.nodekey_assetsinfo_mapper[key]
        return info.assets_amount

    @classmethod
    def test_it(cls):
        from assets.models import Node, Asset

        nodes = list(Node.objects.all())
        nodes_assets = Asset.nodes.through.objects.all() \
            .annotate(aid=F('asset_id')) \
            .values_list('node__key', 'aid')

        mapping = defaultdict(set)
        for key, asset_id in nodes_assets:
            asset_id = str(asset_id)
            mapping[key].add(asset_id)

        util = cls(nodes, mapping)
        util.generate()
        return util
