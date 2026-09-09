from collections import defaultdict
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.db.models import CharField, Q
from django.db.models.functions import Cast

from assets.models import Asset, FavoriteAsset, FavoriteFolder
from perms.models import PermNode
from perms.utils.user_perm import UserPermAssetUtil


FAVORITE_ROOT_ID = 'favorite-root'
AUTHORIZATION_METRIC_CACHE_TIMEOUT = 15
# Keep SQL prefix predicates bounded. Large, scattered grant sets are matched
# against node paths in Python while the database scans the requested subtree.
SUBTREE_QUERY_KEY_LIMIT = 100


def _subtree_filter(keys):
    query = Q()
    for key in PermNode.clean_children_keys(keys):
        query |= Q(node__key=key) | Q(node__key__startswith=f'{key}:')
    return query


def _collect_assets_by_target_key(relations, target_keys, assets_by_key):
    matches_by_node_key = {}
    for asset_id, node_key in relations:
        matched_keys = matches_by_node_key.get(node_key)
        if matched_keys is None:
            matched_keys = []
            current = node_key
            while current:
                if current in target_keys:
                    matched_keys.append(current)
                current = current.rpartition(':')[0]
            matches_by_node_key[node_key] = matched_keys
        for key in matched_keys:
            assets_by_key[key].add(asset_id)


def _collect_granted_assets_by_target_key(
        relations, target_keys, granted_keys, assets_by_key
):
    matches_by_node_key = {}
    for asset_id, node_key in relations:
        match = matches_by_node_key.get(node_key)
        if match is None:
            matched_targets = []
            is_granted = False
            current = node_key
            while current:
                if current in target_keys:
                    matched_targets.append(current)
                if current in granted_keys:
                    is_granted = True
                current = current.rpartition(':')[0]
            match = matched_targets, is_granted
            matches_by_node_key[node_key] = match
        matched_targets, is_granted = match
        if not is_granted:
            continue
        for key in matched_targets:
            assets_by_key[key].add(asset_id)


def _count_assets_by_target_key(relations, target_keys):
    counts = defaultdict(int)
    matches_by_node_key = {}
    current_asset = None
    current_matches = set()
    relations = (
        relations.annotate(asset_key=Cast('asset_id', CharField()))
        .order_by('asset_key', 'node__key')
        .values_list('asset_key', 'node__key')
    )
    for asset_id, node_key in relations.iterator(chunk_size=10000):
        if current_asset is not None and asset_id != current_asset:
            for key in current_matches:
                counts[key] += 1
            current_matches.clear()
        current_asset = asset_id

        matched_keys = matches_by_node_key.get(node_key)
        if matched_keys is None:
            matched_keys = []
            current = node_key
            while current:
                if current in target_keys:
                    matched_keys.append(current)
                current = current.rpartition(':')[0]
            matches_by_node_key[node_key] = matched_keys
        current_matches.update(matched_keys)

    if current_asset is not None:
        for key in current_matches:
            counts[key] += 1
    return counts


def _key_batches(keys):
    keys = list(keys)
    for index in range(0, len(keys), SUBTREE_QUERY_KEY_LIMIT):
        yield set(keys[index:index + SUBTREE_QUERY_KEY_LIMIT])


def _granted_keys_in_targets(granted_keys, target_keys):
    return {
        granted_key for granted_key in granted_keys
        if any(
            granted_key == target_key or
            granted_key.startswith(f'{target_key}:')
            for target_key in target_keys
        )
    }


def _uuid_values(values):
    result = []
    for value in values:
        try:
            result.append(UUID(str(value)))
        except (TypeError, ValueError, AttributeError):
            continue
    return result


def _authorization_node_counts(user, resource_ids, asset_util):
    counts = {}
    if PermNode.UNGROUPED_NODE_KEY in resource_ids:
        counts[PermNode.UNGROUPED_NODE_KEY] = (
            asset_util.get_direct_assets_count()
        )

    node_ids = _uuid_values(resource_ids)
    nodes = list(
        PermNode.objects.filter(id__in=node_ids)
        .only('id', 'key', 'org_id')
    )
    cache_keys = {
        node.id: (
            f'perms:user-granted-tree:{user.id}:{node.org_id}:'
            f'asset-count:{node.id}'
        )
        for node in nodes
    }
    cached = cache.get_many(cache_keys.values())
    missing = []
    for node in nodes:
        cache_key = cache_keys[node.id]
        if cache_key in cached:
            counts[str(node.id)] = cached[cache_key]
        else:
            missing.append(node)
    if not missing:
        return counts

    root_nodes = [
        node for node in missing
        if node.is_org_root() and asset_util.is_node_fully_granted(node.key)
    ]
    if root_nodes:
        root_counts = {
            node.id: Asset.objects.filter(org_id=node.org_id).count()
            for node in root_nodes
        }
        cache.set_many({
            cache_keys[node_id]: amount
            for node_id, amount in root_counts.items()
        }, timeout=AUTHORIZATION_METRIC_CACHE_TIMEOUT)
        counts.update({
            str(node_id): amount for node_id, amount in root_counts.items()
        })
        root_node_ids = set(root_counts)
        missing = [node for node in missing if node.id not in root_node_ids]
        if not missing:
            return counts

    nodes_by_key = {node.key: node for node in missing}
    target_keys = set(nodes_by_key)
    assets_by_key = defaultdict(set)
    fully_granted_keys = {
        key for key in target_keys
        if asset_util.is_node_fully_granted(key)
    }
    fully_granted_counts = {}
    if fully_granted_keys:
        for target_batch in _key_batches(fully_granted_keys):
            relations = Asset.nodes.through.objects.filter(
                _subtree_filter(target_batch)
            )
            fully_granted_counts.update(_count_assets_by_target_key(
                relations, target_batch
            ))

    partial_target_keys = target_keys - fully_granted_keys
    granted_keys = asset_util.direct_node_key_set
    for target_batch in _key_batches(partial_target_keys):
        if granted_keys:
            granted_scan_keys = _granted_keys_in_targets(
                granted_keys, target_batch
            )
            if granted_scan_keys:
                # A few grants are most efficient as indexed subtree queries.
                # For a scattered large grant set, query the target subtree once
                # and decide grant coverage with ancestor-set lookups in Python.
                relations = (
                    Asset.nodes.through.objects.order_by()
                    .filter(_subtree_filter(
                        granted_scan_keys
                        if len(granted_scan_keys) <= SUBTREE_QUERY_KEY_LIMIT
                        else target_batch
                    ))
                    .values_list('asset_id', 'node__key')
                )
                if len(granted_scan_keys) <= SUBTREE_QUERY_KEY_LIMIT:
                    _collect_assets_by_target_key(
                        relations.iterator(chunk_size=10000),
                        target_batch,
                        assets_by_key,
                    )
                else:
                    _collect_granted_assets_by_target_key(
                        relations.iterator(chunk_size=10000),
                        target_batch,
                        granted_keys,
                        assets_by_key,
                    )

        if not settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            direct_relations = (
                Asset.nodes.through.objects.order_by()
                .filter(asset_id__in=asset_util.direct_asset_ids)
                .filter(_subtree_filter(target_batch))
                .values_list('asset_id', 'node__key')
            )
            _collect_assets_by_target_key(
                direct_relations.iterator(chunk_size=10000),
                target_batch,
                assets_by_key,
            )

    computed = {
        node.id: (
            fully_granted_counts.get(node.key, 0)
            if node.key in fully_granted_keys else
            len(assets_by_key[node.key])
        )
        for node in missing
    }

    if computed:
        cache.set_many({
            cache_keys[node_id]: amount
            for node_id, amount in computed.items()
        }, timeout=AUTHORIZATION_METRIC_CACHE_TIMEOUT)
    counts.update({str(node_id): amount for node_id, amount in computed.items()})
    return counts


def _favorite_counts(user, resource_ids):
    folders = list(
        FavoriteFolder.objects.filter(user=user).values('id', 'parent_id')
    )
    parent_by_id = {
        folder['id']: folder['parent_id'] for folder in folders
    }
    requested_folder_ids = (
        set(_uuid_values(resource_ids)) & set(parent_by_id)
    )
    counts = {str(folder_id): 0 for folder_id in requested_folder_ids}
    counts[FAVORITE_ROOT_ID] = 0
    valid_asset_ids = Asset.objects.all().valid().values('id')
    favorites = FavoriteAsset.objects.filter(
        user=user, asset_id__in=valid_asset_ids,
    ).values_list('asset_id', 'folder_id')
    valid_assets = set()
    for asset_id, folder_id in favorites:
        valid_assets.add(asset_id)
        counts[FAVORITE_ROOT_ID] += 1
        visited = set()
        current = folder_id
        while current and current not in visited:
            visited.add(current)
            if current in requested_folder_ids:
                counts[str(current)] += 1
            current = parent_by_id.get(current)
    return counts, valid_assets


def get_user_asset_tree_metrics(user, resources, tree):
    node_ids = [
        item['id'] for item in resources if item['type'] == 'node'
    ]
    asset_ids = _uuid_values(
        item['id'] for item in resources if item['type'] == 'asset'
    )
    if tree == 'favorite':
        node_counts, valid_asset_ids = _favorite_counts(user, node_ids)
        visible_asset_ids = set(asset_ids) & valid_asset_ids
    else:
        asset_util = UserPermAssetUtil(user)
        node_counts = _authorization_node_counts(
            user, node_ids, asset_util
        )
        if asset_ids:
            visible_asset_ids = set(
                asset_util.get_all_assets()
                .filter(id__in=asset_ids).values_list('id', flat=True)
            )
        else:
            visible_asset_ids = set()

    results = []
    for item in resources:
        resource_type = item['type']
        resource_id = item['id']
        if resource_type == 'node':
            if resource_id not in node_counts:
                continue
            count = node_counts[resource_id]
        else:
            try:
                asset_id = UUID(resource_id)
            except (TypeError, ValueError, AttributeError):
                continue
            if asset_id not in visible_asset_ids:
                continue
            count = 1
        results.append({
            'type': resource_type,
            'id': resource_id,
            'count': count,
        })
    return results
