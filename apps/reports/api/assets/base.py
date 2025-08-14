from django.db.models import Count, F


def group_stats(queryset, alias, key, label_map=None):
    grouped = (
        queryset
        .exclude(**{f"{key}__isnull": True})
        .annotate(**{alias: F(key)})
        .values(alias)
        .order_by(alias)
        .annotate(total=Count(1))
    )

    data = [
        {
            alias: g[alias],
            'total': g['total'],
            **({'label': label_map.get(g[alias], g[alias])} if label_map else {})
        }
        for g in grouped
    ]
    return data
