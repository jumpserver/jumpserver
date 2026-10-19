from collections import defaultdict

from django.db.models import Count, Q

from assets.models import Asset, Node
from .models import Account


def _sum_account_counts_by_node(relations, account_counts, target_keys):
    """Count each asset's accounts once per requested ancestor node."""
    seen_assets = defaultdict(set)
    totals = {key: 0 for key in target_keys}
    ancestors_by_key = {}
    for asset_id, node_key in relations:
        count = account_counts.get(asset_id, 0)
        if not count:
            continue
        if node_key not in ancestors_by_key:
            ancestors = []
            key = node_key
            while key:
                if key in target_keys:
                    ancestors.append(key)
                key = key.rpartition(':')[0]
            ancestors_by_key[node_key] = ancestors
        for key in ancestors_by_key[node_key]:
            if asset_id not in seen_assets[key]:
                totals[key] += count
                seen_assets[key].add(asset_id)
    return totals


def get_node_account_counts(nodes, accounts=None, include_descendants=True):
    """Batch exact account counts, deduplicating assets across subtree nodes.

    Aggregate accounts per asset in SQL before traversing asset/node relations,
    so assets with many accounts do not multiply the rows transferred to Python.
    Only requested subtrees are scanned, independently for each organization.
    """
    nodes = list(nodes)
    totals = {node.id: 0 for node in nodes}
    if accounts is None:
        accounts = Account.objects.all()
    by_org = defaultdict(list)
    for node in nodes:
        by_org[node.org_id].append(node)

    for org_id, org_nodes in by_org.items():
        org_accounts = accounts.filter(org_id=org_id, asset__org_id=org_id).order_by()
        if not include_descendants:
            rows = (
                org_accounts.filter(asset__nodes__id__in=[n.id for n in org_nodes])
                .values('asset__nodes__id')
                .annotate(count=Count('id', distinct=True))
            )
            totals.update({row['asset__nodes__id']: row['count'] for row in rows})
            continue

        nodes_by_key = {node.key: node for node in org_nodes}
        descendant_filter = Q()
        for key in Node.clean_children_keys(nodes_by_key):
            descendant_filter |= Q(key=key) | Q(key__startswith=f'{key}:')
        descendant_ids = Node.objects.filter(
            descendant_filter, org_id=org_id,
        ).order_by().values('id')
        relations = Asset.nodes.through.objects.filter(
            node_id__in=descendant_ids,
        ).order_by()
        account_counts = dict(
            org_accounts.filter(asset_id__in=relations.values('asset_id'))
            .values('asset_id')
            .annotate(count=Count('id'))
            .values_list('asset_id', 'count')
        )
        if not account_counts:
            continue
        counts_by_key = _sum_account_counts_by_node(
            relations.values_list('asset_id', 'node__key').iterator(chunk_size=10000),
            account_counts, set(nodes_by_key),
        )
        totals.update({nodes_by_key[key].id: count for key, count in counts_by_key.items()})
    return totals


def get_asset_account_counts(asset_ids, accounts):
    """Match the asset account list, including joined directory service accounts."""
    visible_ids = list(
        Asset.objects.filter(id__in=asset_ids).order_by().values_list('id', flat=True)
    )
    if not visible_ids:
        return {}
    account_owner_ids = {asset_id: {asset_id} for asset_id in visible_ids}
    relations = Asset.directory_services.through.objects.filter(
        asset_id__in=visible_ids,
    ).values_list('asset_id', 'directoryservice_id')
    for asset_id, directory_id in relations:
        account_owner_ids[asset_id].add(directory_id)
    counts = dict(
        accounts.filter(asset_id__in=set().union(*account_owner_ids.values())).order_by()
        .values('asset_id').annotate(count=Count('id', distinct=True))
        .values_list('asset_id', 'count')
    )
    return {
        asset_id: sum(counts.get(owner_id, 0) for owner_id in owner_ids)
        for asset_id, owner_ids in account_owner_ids.items()
    }


def get_account_tree_metrics(resources, accounts=None, include_descendants=True):
    """Return counts for visible nodes/assets, using their stable resource IDs."""
    if accounts is None:
        accounts = Account.objects.all()
    node_ids = [item['id'] for item in resources if item['type'] == 'node']
    asset_ids = [item['id'] for item in resources if item['type'] == 'asset']
    nodes = Node.objects.filter(id__in=node_ids).only('id', 'key', 'org_id')
    node_counts = get_node_account_counts(
        nodes, accounts=accounts, include_descendants=include_descendants,
    )
    asset_counts = get_asset_account_counts(asset_ids, accounts)
    counts_by_type = {'node': node_counts, 'asset': asset_counts}
    return [
        {'type': item['type'], 'id': str(item['id']), 'count': counts_by_type[item['type']][item['id']]}
        for item in resources if item['id'] in counts_by_type[item['type']]
    ]
