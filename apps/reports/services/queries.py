"""Bounded queries used by audit reports."""
from collections import Counter
from uuid import UUID

from django.db.models import Count


def session_platform_counts(sessions, assets, batch_size=500):
    """Resolve platforms once per asset, using indexed primary-key lookups.

    Both querysets must already have the caller's organization scope. Grouped
    keyset pages bound memory even on database drivers that buffer results.
    Historic non-UUID IDs and deleted/out-of-scope assets remain unclassified.
    """
    counts = Counter()
    grouped = sessions.order_by('asset_id').values('asset_id').annotate(count=Count('id'))
    last_asset_id = None
    while True:
        page = grouped if last_asset_id is None else grouped.filter(asset_id__gt=last_asset_id)
        rows = list(page[:batch_size])
        if not rows:
            break
        asset_ids = {}
        for row in rows:
            try:
                asset_ids[row['asset_id']] = UUID(row['asset_id'])
            except (ValueError, TypeError, AttributeError):
                continue
        platforms = dict(assets.filter(pk__in=set(asset_ids.values())).order_by().values_list('id', 'platform__name'))
        for row in rows:
            counts[platforms.get(asset_ids.get(row['asset_id']))] += row['count']
        if len(rows) < batch_size:
            break
        last_asset_id = rows[-1]['asset_id']
    return counts


def es_counts(store, filters, categories):
    """Get exact total/category counts in one request, including on ES 6.

    A filter aggregation for the total avoids the search API's hit-count cap.
    Missing/partial results must fail rather than become misleading zeros.
    """
    response = store.es.search(index=store.query_index, body={
        'query': {'bool': {'filter': filters}}, 'size': 0,
        'aggs': {
            'total': {'filter': {'match_all': {}}},
            'categories': {'filters': {'filters': categories}},
        },
    })
    if response.get('timed_out') or response.get('_shards', {}).get('failed', 0):
        raise RuntimeError('Partial Elasticsearch aggregation')
    aggregations = response['aggregations']
    buckets = aggregations['categories']['buckets']
    return aggregations['total']['doc_count'], {key: buckets[key]['doc_count'] for key in categories}
