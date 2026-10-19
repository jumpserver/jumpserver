from collections import defaultdict

from django.db.models import Q

from ..models import Asset, Node
from .node import _count_assets_by_target_key, get_nodes_realtime_assets_amount


MAX_SEARCH_ASSET_RELATIONS = 5000
MAX_ASSET_SEARCH_RESULTS = 100
MAX_SEARCH_TREE_ROWS = 5000


def _select_nodes_within_tree_budget(
        nodes, max_tree_rows=MAX_SEARCH_TREE_ROWS
):
    accepted_nodes = []
    ancestor_keys = set()
    truncated = False
    for node in nodes:
        node_ancestor_keys = set(node.get_ancestor_keys(with_self=True))
        projected_rows = len(ancestor_keys | node_ancestor_keys)
        if projected_rows > max_tree_rows:
            truncated = True
            continue
        ancestor_keys.update(node_ancestor_keys)
        accepted_nodes.append(node)
    return accepted_nodes, ancestor_keys, truncated


def _select_relations_within_tree_budget(
        relation_rows, max_tree_rows=MAX_SEARCH_TREE_ROWS
):
    """Keep complete paths while bounding node and asset tree rows."""
    accepted_rows = []
    ancestor_keys = set()
    truncated = False
    for row in relation_rows:
        node_key = row[2]
        relation_ancestor_keys = set(Node.get_node_ancestor_keys(
            node_key, with_self=True
        ))
        new_ancestor_keys = relation_ancestor_keys - ancestor_keys
        projected_rows = (
            len(ancestor_keys) + len(new_ancestor_keys) +
            len(accepted_rows) + 1
        )
        if projected_rows > max_tree_rows:
            truncated = True
            continue
        ancestor_keys.update(new_ancestor_keys)
        accepted_rows.append(row)
    return accepted_rows, ancestor_keys, truncated


def _serialize_search_node(
        node, response_parent_keys, asset_parent_keys=(), matched=False
):
    open_node = bool(
        node.key in response_parent_keys or
        node.key in asset_parent_keys
    )
    tree_key = node.key
    resource_id = str(node.id)
    return {
        'id': tree_key,
        'tree_key': tree_key,
        'resource_id': resource_id,
        'name': node.value,
        'title': node.value,
        'pId': node.parent_key,
        'open': open_node,
        'meta': {
            'type': 'node',
            'data': {
                'id': resource_id,
                'resource_id': resource_id,
                'tree_key': tree_key,
                'key': node.key,
                'value': node.value,
                'matched': matched,
            },
        },
    }


def _serialize_search_asset(asset, node=None, detached=False):
    resource_id = str(asset.id)
    is_root_result = node is None
    orphan = is_root_result and not detached
    if is_root_result:
        suffix = 'search' if detached else 'orphan'
        tree_key = f'asset:{resource_id}@{suffix}'
        parent_key = ''
        node_id = None
        node_key = None
    else:
        tree_key = f'asset:{resource_id}@node:{node.id}'
        parent_key = node.key
        node_id = str(node.id)
        node_key = node.key
    platform = asset.platform
    return {
        'id': tree_key,
        'tree_key': tree_key,
        'resource_id': resource_id,
        'name': asset.name,
        'title': asset.address,
        'pId': parent_key,
        'isParent': False,
        'hasChildren': False,
        'open': False,
        'iconSkin': asset.get_icon_skin(),
        'chkDisabled': not asset.is_active,
        'meta': {
            'type': 'asset',
            'data': {
                'id': resource_id,
                'resource_id': resource_id,
                'tree_key': tree_key,
                'name': asset.name,
                'address': asset.address,
                'platform_type': platform.type,
                'node_id': node_id,
                'node_key': node_key,
                'orphan': orphan,
                'search_root': detached,
                'matched': True,
            },
        },
    }


def _with_target_metadata(result, target):
    """Expose generic and per-resource metadata from the same result."""
    return {
        **result,
        f'matched_{target}_count': result['matched_count'],
        f'returned_{target}_count': result['returned_count'],
        f'{target}_truncated': result['truncated'],
        f'{target}_limit': result['limit'],
    }


def _search_nodes(
        search, limit, max_tree_rows=MAX_SEARCH_TREE_ROWS):
    matches = Node.objects.filter(value__icontains=search)
    matched_nodes = list(matches.order_by('key')[:limit + 1])
    matches_truncated = len(matched_nodes) > limit
    matched_count = len(matched_nodes)
    matched_nodes = matched_nodes[:limit]
    matched_nodes, ancestor_keys, tree_budget_truncated = (
        _select_nodes_within_tree_budget(
            matched_nodes, max_tree_rows=max_tree_rows,
        )
    )

    nodes = list(
        Node.objects.filter(key__in=ancestor_keys)
        .only('id', 'key', 'value', 'parent_key', 'org_id')
        .order_by('key')
    )
    response_parent_keys = {
        node.parent_key for node in nodes if node.parent_key
    }
    matched_node_ids = {node.id for node in matched_nodes}
    tree = [
        _serialize_search_node(
            node, response_parent_keys,
            matched=node.id in matched_node_ids,
        )
        for node in nodes
    ]
    truncated = matches_truncated or tree_budget_truncated
    return _with_target_metadata({
        'tree': tree,
        'matched_count': matched_count,
        'returned_count': len(matched_nodes),
        'truncated': truncated,
        'has_more': truncated,
        'limit': limit,
    }, 'node')


def _search_assets(
        search, limit, max_tree_rows=MAX_SEARCH_TREE_ROWS,
        include_ancestors=True):
    matches = Asset.objects.filter(
        Q(name__icontains=search) | Q(address__icontains=search)
    )
    matches = matches.distinct()
    assets = list(
        matches.select_related('platform')
        .only(
            'id', 'name', 'address', 'platform_id', 'is_active',
            'platform__type', 'platform__category',
        )
        .order_by('name', 'address', 'id')[:limit + 1]
    )
    matches_truncated = len(assets) > limit
    matched_count = len(assets)
    assets = assets[:limit]

    if not include_ancestors:
        tree = [
            _serialize_search_asset(asset, detached=True)
            for asset in assets
        ]
        return _with_target_metadata({
            'tree': tree,
            'matched_count': matched_count,
            'returned_count': len(tree),
            'truncated': matches_truncated,
            'has_more': matches_truncated,
            'limit': limit,
        }, 'asset')

    assets_by_id = {asset.id: asset for asset in assets}

    related_asset_ids = set(
        Asset.nodes.through.objects.filter(
            asset_id__in=assets_by_id.keys()
        ).values_list('asset_id', flat=True).distinct()
    )
    orphan_asset_ids = set(assets_by_id) - related_asset_ids
    orphan_assets = [
        asset for asset in assets if asset.id in orphan_asset_ids
    ]

    relations = Asset.nodes.through.objects.filter(
        asset_id__in=assets_by_id.keys()
    )
    relation_rows = list(
        relations.order_by('node__key', 'asset_id')
        .values_list('asset_id', 'node_id', 'node__key')
        [:MAX_SEARCH_ASSET_RELATIONS + 1]
    )
    relations_truncated = len(relation_rows) > MAX_SEARCH_ASSET_RELATIONS
    relation_rows = relation_rows[:MAX_SEARCH_ASSET_RELATIONS]
    relation_rows, ancestor_keys, tree_budget_truncated = (
        _select_relations_within_tree_budget(
            relation_rows,
            max_tree_rows=max(0, max_tree_rows - len(orphan_assets)),
        )
    )

    asset_nodes = defaultdict(list)
    node_ids = set()
    for asset_id, node_id, node_key in relation_rows:
        asset_nodes[asset_id].append(node_id)
        node_ids.add(node_id)

    nodes = list(
        Node.objects.filter(key__in=ancestor_keys)
        .only('id', 'key', 'value', 'parent_key', 'org_id')
        .order_by('key')
    )
    nodes_by_id = {node.id: node for node in nodes if node.id in node_ids}
    response_parent_keys = {
        node.parent_key for node in nodes if node.parent_key
    }
    asset_parent_keys = {node.key for node in nodes_by_id.values()}
    tree = [
        _serialize_search_node(
            node, response_parent_keys, asset_parent_keys
        )
        for node in nodes
    ]
    returned_asset_ids = set()
    for asset in assets:
        for node_id in asset_nodes.get(asset.id, ()):
            node = nodes_by_id.get(node_id)
            if not node:
                continue
            returned_asset_ids.add(asset.id)
            tree.append(_serialize_search_asset(asset, node))
    for asset in orphan_assets:
        returned_asset_ids.add(asset.id)
        tree.append(_serialize_search_asset(asset))

    truncated = (
        matches_truncated or relations_truncated or
        tree_budget_truncated or
        len(returned_asset_ids) < len(assets)
    )
    return _with_target_metadata({
        'tree': tree,
        'matched_count': matched_count,
        'returned_count': len(returned_asset_ids),
        'truncated': truncated,
        'has_more': truncated,
        'limit': limit,
    }, 'asset')


def _merge_search_tree_rows(*trees):
    """Merge complete node paths while retaining each match annotation."""
    rows = []
    rows_by_identity = {}
    for tree in trees:
        for item in tree:
            resource_type = item.get('meta', {}).get('type', 'node')
            identity = (resource_type, item.get('id'))
            existing = rows_by_identity.get(identity)
            if existing is None:
                copied = {
                    **item,
                    'meta': {
                        **item.get('meta', {}),
                        'data': dict(item.get('meta', {}).get('data', {})),
                    },
                }
                rows_by_identity[identity] = copied
                rows.append(copied)
                continue

            existing['open'] = bool(existing.get('open') or item.get('open'))
            existing_data = existing['meta']['data']
            item_data = item.get('meta', {}).get('data', {})
            matched = bool(
                existing_data.get('matched') or item_data.get('matched')
            )
            existing_data.update(item_data)
            existing_data['matched'] = matched
    return rows


def search_node_asset_tree(
        search, target, limit, include_ancestors=True
):
    """Search nodes/assets and return only their complete tree paths."""
    if target == 'node':
        return _search_nodes(search, limit)
    if target == 'asset':
        return _search_assets(
            search, min(limit, MAX_ASSET_SEARCH_RESULTS),
            include_ancestors=include_ancestors,
        )
    if target != 'all':
        raise ValueError(f'Unsupported node asset tree search target: {target}')

    # Bound the complete mixed response to the same budget as a single-target
    # search. Each half still has an independent match limit of at most 1000.
    node_budget = MAX_SEARCH_TREE_ROWS // 2
    node_result = _search_nodes(
        search, limit, max_tree_rows=node_budget,
    )
    asset_result = _search_assets(
        search, limit,
        max_tree_rows=MAX_SEARCH_TREE_ROWS - node_budget,
    )
    truncated = node_result['truncated'] or asset_result['truncated']
    return {
        'tree': _merge_search_tree_rows(
            node_result['tree'], asset_result['tree'],
        ),
        'matched_count': (
            node_result['matched_count'] + asset_result['matched_count']
        ),
        'returned_count': (
            node_result['returned_count'] + asset_result['returned_count']
        ),
        'matched_node_count': node_result['matched_node_count'],
        'returned_node_count': node_result['returned_node_count'],
        'node_truncated': node_result['node_truncated'],
        'node_limit': node_result['node_limit'],
        'matched_asset_count': asset_result['matched_asset_count'],
        'returned_asset_count': asset_result['returned_asset_count'],
        'asset_truncated': asset_result['asset_truncated'],
        'asset_limit': asset_result['asset_limit'],
        'truncated': truncated,
        'has_more': truncated,
        'limit': limit,
    }


def get_asset_tree_metrics(items, metric, search=None, fresh=False):
    node_ids = [item['id'] for item in items if item['type'] == 'node']
    asset_ids = [item['id'] for item in items if item['type'] == 'asset']
    nodes = list(
        Node.objects.filter(id__in=node_ids).only('id', 'key', 'org_id')
    )
    nodes_by_id = {node.id: node for node in nodes}
    existing_asset_ids = set(
        Asset.objects.filter(id__in=asset_ids).values_list('id', flat=True)
    )

    if metric in ('asset_all', 'asset_direct'):
        amounts = get_nodes_realtime_assets_amount(
            nodes,
            include_descendants=metric == 'asset_all',
            fresh=fresh,
        )
        asset_matches = existing_asset_ids
    else:
        nodes_by_org = defaultdict(list)
        for node in nodes:
            nodes_by_org[node.org_id].append(node)
        amounts = {}
        for org_id, org_nodes in nodes_by_org.items():
            relations = Asset.nodes.through.objects.order_by().filter(
                node__org_id=org_id,
            ).filter(
                Q(asset__name__icontains=search) |
                Q(asset__address__icontains=search)
            )
            target_keys = {node.key for node in org_nodes}
            descendant_filter = Q()
            for root_key in Node.clean_children_keys(target_keys):
                descendant_filter |= (
                    Q(node__key=root_key) |
                    Q(node__key__startswith=f'{root_key}:')
                )
            relations = relations.filter(descendant_filter)
            amounts_by_key = _count_assets_by_target_key(
                relations.values_list('asset_id', 'node__key')
                .iterator(chunk_size=10000),
                target_keys,
            )
            amounts.update({
                node.id: amounts_by_key[node.key]
                for node in org_nodes
            })
        matched_assets = Asset.objects.filter(id__in=asset_ids).filter(
            Q(name__icontains=search) |
            Q(address__icontains=search)
        )
        asset_matches = set(
            matched_assets.distinct()
            .values_list('id', flat=True)
        )

    results = []
    for item in items:
        resource_type = item['type']
        resource_id = item['id']
        if resource_type == 'node':
            if resource_id not in nodes_by_id:
                continue
            count = amounts.get(resource_id, 0)
        else:
            if resource_id not in existing_asset_ids:
                continue
            count = int(resource_id in asset_matches)
        results.append({
            'type': resource_type,
            'id': str(resource_id),
            'count': count,
        })
    return results
