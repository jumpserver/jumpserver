from django.utils.translation import gettext as _
from rest_framework import serializers

__all__ = ['PermissionTreeMetricsQuerySerializer']


class PermissionTreeMetricItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=(
        'node', 'asset', 'organization', 'user_group', 'user',
    ))
    id = serializers.UUIDField()


class PermissionTreeMetricsQuerySerializer(serializers.Serializer):
    items = PermissionTreeMetricItemSerializer(
        many=True, allow_empty=False, max_length=200
    )
    metric = serializers.ChoiceField(choices=(
        'permission_direct', 'permission_effective', 'direct', 'effective',
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
