# ~*~ coding: utf-8 ~*~
#
from collections import defaultdict
from uuid import uuid4

from django.core.cache import cache
from django.db.models import Count, F, Q

from common.struct import Stack
from common.utils import dict_get_any, is_uuid, get_object_or_none, timeit
from common.utils.http import is_true
from common.utils.lock import DistributedLock
from ..models import Node


NODE_ASSET_AMOUNT_CACHE_TIMEOUT = 5
NODE_ASSET_AMOUNT_FLIGHT_MARKER_TIMEOUT = 30


def _node_assets_amount_cache_key(node, include_descendants):
    scope = 'all' if include_descendants else 'direct'
    return f'assets:node-assets-amount:{node.org_id}:{scope}:{node.id}'


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


def _node_assets_amount_lock_name(
        org_id, include_descendants
):
    scope = 'all' if include_descendants else 'direct'
    return f'assets.node-assets-amount.{org_id}.{scope}'


def _node_assets_amount_flight_marker_key(lock_name):
    return f'assets:node-assets-amount:flight:{lock_name}'


def _node_assets_amount_flight_marker_token(marker):
    if isinstance(marker, dict):
        return marker.get('token')
    return marker


def _node_assets_amount_flight_marker_node_ids(marker):
    if not isinstance(marker, dict):
        return set()
    return set(marker.get('node_ids', ()))


def _node_assets_amount_flight_marker_is_fresh(marker):
    if not isinstance(marker, dict):
        return False
    return marker.get('fresh') is True


def _compute_nodes_assets_amount(
        org_id, nodes, include_descendants
):
    from assets.models import Asset

    relations = Asset.nodes.through.objects.order_by()
    computed = {node.id: 0 for node in nodes}
    if not include_descendants:
        rows = (
            relations.filter(node_id__in=computed)
            .values('node_id')
            .annotate(amount=Count('asset_id', distinct=True))
        )
        computed.update({row['node_id']: row['amount'] for row in rows})
        return computed

    nodes_by_key = {node.key: node for node in nodes}
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
        computed[node.id] = amounts_by_key[key]
    return computed


def get_nodes_realtime_assets_amount(
        nodes, include_descendants=True, fresh=False
):
    """Return asset amounts for a bounded node collection.

    Descendant counts intentionally avoid a correlated subquery per node.
    Relevant M2M rows are read once per organization, then distinct assets are
    accumulated along the materialized node path. All query expressions used
    here are portable across PostgreSQL, MySQL and MariaDB. Ordinary reads may
    reuse a scalar result for five seconds; ``fresh`` bypasses older values,
    while concurrent fresh reads for the same nodes share the completed scan.
    """
    nodes = list(nodes)
    amounts = {node.id: 0 for node in nodes}
    if not nodes:
        return amounts

    nodes_by_org = defaultdict(list)
    for node in nodes:
        nodes_by_org[node.org_id].append(node)

    for org_id, org_nodes in nodes_by_org.items():
        cache_keys = {
            node.id: _node_assets_amount_cache_key(node, include_descendants)
            for node in org_nodes
        }
        cached = {} if fresh else cache.get_many(cache_keys.values())
        missing_nodes = []
        for node in org_nodes:
            cache_key = cache_keys[node.id]
            if cache_key in cached:
                amounts[node.id] = cached[cache_key]
            else:
                missing_nodes.append(node)
        if not missing_nodes:
            continue

        # Both ordinary cold loads and explicit fresh reads share one lock per
        # organization and scope. This prevents overlapping batches from
        # scanning the same relation table or overwriting a newer fresh read.
        lock_name = _node_assets_amount_lock_name(
            org_id, include_descendants
        )
        marker_key = _node_assets_amount_flight_marker_key(lock_name)
        observed_marker = cache.get(marker_key) if fresh else None
        requested_node_ids = [str(node.id) for node in missing_nodes]
        with DistributedLock(lock_name):
            current_marker = cache.get(marker_key) if fresh else None
            another_flight_completed = bool(
                fresh and
                _node_assets_amount_flight_marker_is_fresh(current_marker) and
                _node_assets_amount_flight_marker_token(current_marker) and
                _node_assets_amount_flight_marker_token(current_marker) !=
                _node_assets_amount_flight_marker_token(observed_marker)
            )
            completed_node_ids = (
                _node_assets_amount_flight_marker_node_ids(current_marker)
                if another_flight_completed else set()
            )
            reusable_nodes = [
                node for node in missing_nodes
                if not fresh or str(node.id) in completed_node_ids
            ]
            if reusable_nodes:
                cached = cache.get_many([
                    cache_keys[node.id] for node in reusable_nodes
                ])
                reusable_node_ids = {node.id for node in reusable_nodes}
                still_missing = []
                for node in missing_nodes:
                    cache_key = cache_keys[node.id]
                    if node.id in reusable_node_ids and cache_key in cached:
                        amounts[node.id] = cached[cache_key]
                    else:
                        still_missing.append(node)
                missing_nodes = still_missing
            if not missing_nodes:
                continue

            computed = _compute_nodes_assets_amount(
                org_id, missing_nodes, include_descendants
            )
            amounts.update(computed)
            cache.set_many(
                {
                    cache_keys[node_id]: amount
                    for node_id, amount in computed.items()
                },
                timeout=NODE_ASSET_AMOUNT_CACHE_TIMEOUT,
            )
            cache.set(
                marker_key, {
                    'token': uuid4().hex,
                    'node_ids': requested_node_ids,
                    'fresh': fresh,
                },
                timeout=NODE_ASSET_AMOUNT_FLIGHT_MARKER_TIMEOUT,
            )

    return amounts


def attach_nodes_realtime_assets_amount(
        nodes, include_descendants=True, fresh=False
):
    nodes = list(nodes)
    amounts = get_nodes_realtime_assets_amount(
        nodes, include_descendants=include_descendants, fresh=fresh
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
