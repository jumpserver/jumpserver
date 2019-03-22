# -*- coding: utf-8 -*-
from rest_framework import serializers

from ..models import Asset, Node


__all__ = [
    'NodeSerializer', "NodeAddChildrenSerializer",
    "NodeAssetsSerializer",
]


class NodeSerializer(serializers.ModelSerializer):
    assets_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Node
        fields = [
            'id', 'key', 'value', 'assets_amount', 'org_id',
        ]
        read_only_fields = [
            'key', 'assets_amount', 'org_id',
        ]

    def validate_value(self, data):
        instance = self.instance if self.instance else Node.root()
        children = instance.parent.get_children().exclude(key=instance.key)
        values = [child.value for child in children]
        if data in values:
            raise serializers.ValidationError(
                'The same level node name cannot be the same'
            )
        return data


class NodeAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Node
        fields = ['assets']


class NodeAddChildrenSerializer(serializers.Serializer):
    nodes = serializers.ListField()

