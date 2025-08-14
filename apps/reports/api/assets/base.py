from django.db.models import Count, F


def group_stats(queryset, alias, key, label_map=None):
    pk_name = queryset.model._meta.pk.name

    base = (
        queryset.order_by()
        .exclude(**{f"{key}__isnull": True})
        .annotate(**{alias: F(key)})
        .values(pk_name, alias)
        .distinct()
    )

    grouped = base.values(alias).annotate(total=Count(pk_name))

    data = [
        {
            alias: val,
            'total': cnt,
            **({'label': label_map.get(val, val)} if label_map else {})
        }
        for val, cnt in grouped.values_list(alias, 'total')
    ]
    return data
