from django.db.models import Count, F


def group_stats(queryset, alias, key, label_map=None):
    grouped = (
        queryset
        .exclude(**{f'{key}__isnull': True})
        .values(**{alias: F(key)})
        .annotate(total=Count('id'))
    )

    data = [
        {
            alias: val,
            'total': cnt,
            **({'label': label_map.get(val, val)} if label_map else {})
        }
        for val, cnt in grouped.values_list(alias, 'total')
    ]

    return data
