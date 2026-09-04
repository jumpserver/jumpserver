from collections import defaultdict

from assets.models import Asset, Node
from orgs.utils import current_org
from perms.models import AssetPermission
from users.models import User, UserGroup


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
    is_effective = metric in ('permission_effective', 'effective')
    node_ids = [item['id'] for item in items if item['type'] == 'node']
    asset_ids = [item['id'] for item in items if item['type'] == 'asset']
    group_ids = [
        item['id'] for item in items if item['type'] == 'user_group'
    ]
    user_ids = [item['id'] for item in items if item['type'] == 'user']
    nodes = list(
        Node.objects.filter(id__in=node_ids).only('id', 'key', 'org_id')
    )
    assets = list(
        Asset.objects.filter(id__in=asset_ids).only('id', 'org_id')
    )
    groups = list(UserGroup.objects.filter(id__in=group_ids).only('id'))
    users = list(
        User.get_org_users(current_org).filter(id__in=user_ids).only('id')
    )
    nodes_by_id = {node.id: node for node in nodes}
    assets_by_id = {asset.id: asset for asset in assets}
    groups_by_id = {group.id: group for group in groups}
    users_by_id = {user.id: user for user in users}

    permission_ids = AssetPermission.objects.order_by().values('id')
    node_permission_rows = AssetPermission.nodes.through.objects.filter(
        assetpermission_id__in=permission_ids,
        node_id__in=nodes_by_id.keys(),
    ).values_list('node_id', 'assetpermission_id')
    asset_permission_rows = AssetPermission.assets.through.objects.filter(
        assetpermission_id__in=permission_ids,
        asset_id__in=assets_by_id.keys(),
    ).values_list('asset_id', 'assetpermission_id')
    user_permission_rows = AssetPermission.users.through.objects.filter(
        assetpermission_id__in=permission_ids,
        user_id__in=users_by_id.keys(),
    ).values_list('user_id', 'assetpermission_id').distinct()

    permissions_by_node_id = defaultdict(set)
    for node_id, permission_id in node_permission_rows:
        permissions_by_node_id[node_id].add(permission_id)
    permissions_by_asset_id = defaultdict(set)
    for asset_id, permission_id in asset_permission_rows:
        permissions_by_asset_id[asset_id].add(permission_id)

    permissions_by_user_id = defaultdict(set)
    for user_id, permission_id in user_permission_rows:
        permissions_by_user_id[user_id].add(permission_id)

    if is_effective and users_by_id:
        effective_group_rows = (
            AssetPermission.user_groups.through.objects.filter(
                assetpermission_id__in=permission_ids,
                usergroup_id__in=UserGroup.objects.order_by().values('id'),
                usergroup__users__id__in=users_by_id.keys(),
            )
            .values_list('usergroup__users__id', 'assetpermission_id')
            .distinct()
        )
        for user_id, permission_id in effective_group_rows:
            permissions_by_user_id[user_id].add(permission_id)

    group_permission_rows = (
        AssetPermission.user_groups.through.objects.filter(
            assetpermission_id__in=permission_ids,
            usergroup_id__in=groups_by_id.keys(),
        ).values_list('usergroup_id', 'assetpermission_id').distinct()
    )
    permissions_by_group_id = defaultdict(set)
    for group_id, permission_id in group_permission_rows:
        permissions_by_group_id[group_id].add(permission_id)

    if is_effective:
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
    organization_requested = any(
        item['type'] == 'organization'
        and str(item['id']) == str(current_org.id)
        for item in items
    )
    organization_count = (
        AssetPermission.objects.order_by().count()
        if organization_requested else None
    )
    for item in items:
        resource_type = item['type']
        resource_id = item['id']
        if resource_type == 'node':
            if resource_id not in nodes_by_id:
                continue
            count = len(permissions_by_node_id[resource_id])
        elif resource_type == 'asset':
            if resource_id not in assets_by_id:
                continue
            count = len(permissions_by_asset_id[resource_id])
        elif resource_type == 'user_group':
            if resource_id not in groups_by_id:
                continue
            count = len(permissions_by_group_id[resource_id])
        elif resource_type == 'user':
            if resource_id not in users_by_id:
                continue
            count = len(permissions_by_user_id[resource_id])
        else:
            if str(resource_id) != str(current_org.id):
                continue
            count = organization_count
        results.append({
            'type': resource_type,
            'id': str(resource_id),
            'count': count,
        })
    return results
