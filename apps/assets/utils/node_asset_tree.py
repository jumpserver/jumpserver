from collections import defaultdict

from django.db.models import Q

from ..models import Asset, Node
from .node import _count_assets_by_target_key, get_nodes_realtime_assets_amount


MAX_SEARCH_ASSET_RELATIONS = 5000
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


def _scope_nodes(queryset, scope_node):
    if not scope_node:
        return queryset
    return queryset.filter(
        Q(key=scope_node.key) |
        Q(key__startswith=f'{scope_node.key}:')
    )


def _serialize_search_node(
        node, response_parent_keys, asset_parent_keys=(), matched=False
):
    has_children = bool(
        getattr(node, 'has_children', False) or
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
        'isParent': has_children,
        'hasChildren': has_children,
        'open': True,
        'meta': {
            'type': 'node',
            'data': {
                'id': resource_id,
                'resource_id': resource_id,
                'tree_key': tree_key,
                'key': node.key,
                'value': node.value,
                'has_children': has_children,
                'matched': matched,
            },
        },
    }


def _serialize_search_asset(asset, node=None):
    resource_id = str(asset.id)
    orphan = node is None
    if orphan:
        tree_key = f'asset:{resource_id}@orphan'
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
                'matched': True,
            },
        },
    }


def search_node_asset_tree(search, target, limit, scope_node=None):
    """Search a node/asset tree without loading the complete asset set."""
    if target == 'node':
        matches = Node.objects.filter(value__icontains=search)
        matches = _scope_nodes(matches, scope_node)
        matched_nodes = list(matches.order_by('key')[:limit + 1])
        matches_truncated = len(matched_nodes) > limit
        matched_count = len(matched_nodes)
        matched_nodes = matched_nodes[:limit]
        matched_nodes, ancestor_keys, tree_budget_truncated = (
            _select_nodes_within_tree_budget(matched_nodes)
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
        return {
            'tree': tree,
            'matched_count': matched_count,
            'returned_count': len(matched_nodes),
            'truncated': matches_truncated or tree_budget_truncated,
            'has_more': matches_truncated or tree_budget_truncated,
            'limit': limit,
        }

    matches = Asset.objects.filter(
        Q(name__icontains=search) | Q(address__icontains=search)
    )
    if scope_node:
        matches = matches.filter(
            Q(nodes__key=scope_node.key) |
            Q(nodes__key__startswith=f'{scope_node.key}:')
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
    assets_by_id = {asset.id: asset for asset in assets}

    orphan_asset_ids = set()
    if not scope_node:
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
    if scope_node:
        relations = relations.filter(
            Q(node__key=scope_node.key) |
            Q(node__key__startswith=f'{scope_node.key}:')
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
            max_tree_rows=MAX_SEARCH_TREE_ROWS - len(orphan_assets),
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
    return {
        'tree': tree,
        'matched_count': matched_count,
        'returned_count': len(returned_asset_ids),
        'truncated': truncated,
        'has_more': truncated,
        'limit': limit,
    }


def get_asset_tree_metrics(
        items, metric, search=None, scope_node=None, fresh=False
):
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
            if scope_node:
                relations = relations.filter(
                    Q(node__key=scope_node.key) |
                    Q(node__key__startswith=f'{scope_node.key}:')
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
        if scope_node:
            matched_assets = matched_assets.filter(
                Q(nodes__key=scope_node.key) |
                Q(nodes__key__startswith=f'{scope_node.key}:')
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
