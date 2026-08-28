from django.utils.translation import gettext as _
from rest_framework import serializers

from assets.serializers.node import TreeMetricItemSerializer


__all__ = ['PermissionTreeMetricsQuerySerializer']


class PermissionTreeMetricsQuerySerializer(serializers.Serializer):
    items = TreeMetricItemSerializer(
        many=True, allow_empty=False, max_length=200
    )
    metric = serializers.ChoiceField(choices=(
        'permission_direct', 'permission_effective',
    ))

    def validate_items(self, items):
        seen = set()
        result = []
        for item in items:
            identity = (item['type'], item['id'])
            if identity in seen:
                continue
            seen.add(identity)
            result.append(item)
        if not result:
            raise serializers.ValidationError(_('This list may not be empty.'))
        return result
