from collections import defaultdict

from assets.models import Asset, Node
from perms.models import AssetPermission


ANCESTOR_QUERY_BATCH_SIZE = 500


def _chunked(values, size=ANCESTOR_QUERY_BATCH_SIZE):
    values = list(values)
    for start in range(0, len(values), size):
        yield values[start:start + size]


def _ancestor_keys(org_id, key):
    return {
        (org_id, ancestor_key)
        for ancestor_key in Node.get_node_ancestor_keys(key, with_self=True)
    }


def get_permission_tree_metrics(items, metric):
    """Count direct/inherited permissions for a bounded resource batch."""
    node_ids = [item['id'] for item in items if item['type'] == 'node']
    asset_ids = [item['id'] for item in items if item['type'] == 'asset']
    nodes = list(
        Node.objects.filter(id__in=node_ids).only('id', 'key', 'org_id')
    )
    assets = list(
        Asset.objects.filter(id__in=asset_ids).only('id', 'org_id')
    )
    nodes_by_id = {node.id: node for node in nodes}
    assets_by_id = {asset.id: asset for asset in assets}

    permission_ids = AssetPermission.objects.order_by().values('id')
    node_permission_rows = AssetPermission.nodes.through.objects.filter(
        assetpermission_id__in=permission_ids,
        node_id__in=nodes_by_id.keys(),
    ).values_list('node_id', 'assetpermission_id')
    asset_permission_rows = AssetPermission.assets.through.objects.filter(
        assetpermission_id__in=permission_ids,
        asset_id__in=assets_by_id.keys(),
    ).values_list('asset_id', 'assetpermission_id')

    permissions_by_node_id = defaultdict(set)
    for node_id, permission_id in node_permission_rows:
        permissions_by_node_id[node_id].add(permission_id)
    permissions_by_asset_id = defaultdict(set)
    for asset_id, permission_id in asset_permission_rows:
        permissions_by_asset_id[asset_id].add(permission_id)

    if metric == 'permission_effective':
        node_ancestor_keys = {
            node.id: _ancestor_keys(node.org_id, node.key) for node in nodes
        }
        asset_ancestor_keys = defaultdict(set)
        asset_node_rows = Asset.nodes.through.objects.filter(
            asset_id__in=assets_by_id.keys()
        ).values_list('asset_id', 'node__org_id', 'node__key')
        for asset_id, org_id, node_key in asset_node_rows:
            asset_ancestor_keys[asset_id].update(
                _ancestor_keys(org_id, node_key)
            )

        all_ancestor_keys = set()
        for keys in node_ancestor_keys.values():
            all_ancestor_keys.update(keys)
        for keys in asset_ancestor_keys.values():
            all_ancestor_keys.update(keys)
        keys_by_org = defaultdict(set)
        for org_id, key in all_ancestor_keys:
            keys_by_org[org_id].add(key)
        ancestor_nodes = []
        for org_id, keys in keys_by_org.items():
            for key_batch in _chunked(keys):
                rows = Node.objects.filter(
                    org_id=org_id, key__in=key_batch
                ).values_list('id', 'org_id', 'key')
                ancestor_nodes.extend(rows)
        ancestor_node_ids_by_key = {
            (org_id, key): node_id
            for node_id, org_id, key in ancestor_nodes
        }
        all_ancestor_node_ids = set(ancestor_node_ids_by_key.values())
        ancestor_permission_rows = []
        for node_id_batch in _chunked(all_ancestor_node_ids):
            rows = AssetPermission.nodes.through.objects.filter(
                assetpermission_id__in=permission_ids,
                node_id__in=node_id_batch,
            ).values_list('node_id', 'assetpermission_id')
            ancestor_permission_rows.extend(rows)
        permissions_by_ancestor_node_id = defaultdict(set)
        for node_id, permission_id in ancestor_permission_rows:
            permissions_by_ancestor_node_id[node_id].add(permission_id)

        for node_id, keys in node_ancestor_keys.items():
            permission_set = permissions_by_node_id[node_id]
            for org_key in keys:
                ancestor_id = ancestor_node_ids_by_key.get(org_key)
                if ancestor_id is None:
                    continue
                permission_set.update(
                    permissions_by_ancestor_node_id[ancestor_id]
                )
        for asset_id, keys in asset_ancestor_keys.items():
            permission_set = permissions_by_asset_id[asset_id]
            for org_key in keys:
                ancestor_id = ancestor_node_ids_by_key.get(org_key)
                if ancestor_id is None:
                    continue
                permission_set.update(
                    permissions_by_ancestor_node_id[ancestor_id]
                )

    results = []
    for item in items:
        resource_type = item['type']
        resource_id = item['id']
        if resource_type == 'node':
            if resource_id not in nodes_by_id:
                continue
            count = len(permissions_by_node_id[resource_id])
        else:
            if resource_id not in assets_by_id:
                continue
            count = len(permissions_by_asset_id[resource_id])
        results.append({
            'type': resource_type,
            'id': str(resource_id),
            'count': count,
        })
    return results
