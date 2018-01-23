from collections import defaultdict

from django import template
register = template.Library()


@register.filter
def group_labels(queryset):
    grouped = defaultdict(list)
    for label in queryset:
        grouped[label.name].append(label)
    return [(name, labels) for name, labels in grouped.items()]
