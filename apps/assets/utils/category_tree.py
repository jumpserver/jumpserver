from django.db.models import Count

from assets.const import AllTypes
from assets.models import Asset


def _category_metric_targets(nodes, resources):
    nodes_by_id = {str(node['id']): node for node in nodes}
    return {
        item['id']: nodes_by_id[item['id']]
        for item in resources
        if item['id'] in nodes_by_id
        and nodes_by_id[item['id']].get('meta', {}).get('type') == item['type']
    }


def _category_platform_targets(nodes, targets):
    nodes_by_id = {str(node['id']): node for node in nodes}
    platform_targets = {}
    for node in nodes:
        if node.get('meta', {}).get('type') != 'platform':
            continue
        ancestors = []
        current = node
        while current:
            node_id = str(current['id'])
            if node_id in targets:
                ancestors.append(node_id)
            current = nodes_by_id.get(str(current.get('pId')))
        if ancestors:
            platform_targets[int(node['id'])] = ancestors
    return platform_targets


def get_category_tree_metrics(resources, count_resource='asset'):
    """Aggregate counts in SQL; tree structure never waits for resource counts."""
    nodes = AllTypes.get_tree_nodes((), with_resource_amount=False)
    targets = _category_metric_targets(nodes, resources)
    platform_targets = _category_platform_targets(nodes, targets)
    totals = dict.fromkeys(targets, 0)
    if platform_targets:
        if count_resource == 'account':
            from accounts.models import Account
            queryset = Account.objects.all()
            platform_field = 'asset__platform_id'
        else:
            queryset = Asset.objects.all()
            platform_field = 'platform_id'
        counts = (
            queryset.filter(**{f'{platform_field}__in': platform_targets}).order_by()
            .values(platform_field).annotate(count=Count('id'))
            .values_list(platform_field, 'count')
        )
        for platform_id, count in counts:
            for target_id in platform_targets[platform_id]:
                totals[target_id] += count
    return [
        {'type': item['type'], 'id': item['id'], 'count': totals[item['id']]}
        for item in resources
        if targets.get(item['id'], {}).get('meta', {}).get('type') == item['type']
    ]
