from django.utils.translation import gettext as _
from rest_framework import serializers

from assets.serializers.node import NodeTreeQuerySerializer

__all__ = [
    'PermissionTreeMetricsQuerySerializer',
    'UserAuthorizationTreeQuerySerializer',
    'UserAssetTreeMetricsQuerySerializer',
]


class PermissionTreeMetricItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=(
        'node', 'asset', 'organization', 'user_group', 'ungrouped_users', 'user',
    ))
    id = serializers.UUIDField()


class PermissionTreeMetricsQuerySerializer(serializers.Serializer):
    resources = PermissionTreeMetricItemSerializer(
        many=True, allow_empty=False
    )
    metric = serializers.ChoiceField(choices=(
        'permission_direct', 'permission_effective', 'direct', 'effective',
    ))

    def to_internal_value(self, data):
        data = data.copy()
        if 'resources' not in data and 'items' in data:
            data['resources'] = data['items']
        return super().to_internal_value(data)

    def validate_resources(self, items):
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


class UserAssetTreeMetricItemSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=('node', 'asset'))
    id = serializers.CharField(max_length=128)


class UserAuthorizationTreeQuerySerializer(NodeTreeQuerySerializer):
    """Options shared with the ordinary node/asset tree endpoint."""

    include_asset_count = serializers.BooleanField(default=False)
    include_favorites = serializers.BooleanField(default=False)


class UserAssetTreeMetricsQuerySerializer(serializers.Serializer):
    resources = UserAssetTreeMetricItemSerializer(
        many=True, allow_empty=False
    )
    tree = serializers.ChoiceField(choices=('authorization', 'favorite'))

    @staticmethod
    def validate_resources(resources):
        seen = set()
        result = []
        for item in resources:
            identity = (item['type'], item['id'])
            if identity in seen:
                continue
            seen.add(identity)
            result.append(item)
        return result
