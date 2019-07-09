# -*- coding: utf-8 -*-
from rest_framework import serializers
from django.utils.translation import ugettext as _

from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import Asset, Node


__all__ = [
    'NodeSerializer', "NodeAddChildrenSerializer",
    "NodeAssetsSerializer",
]


class NodeSerializer(BulkOrgResourceModelSerializer):
    assets_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Node
        only_fields = ['id', 'key', 'value', 'org_id']
        fields = only_fields + ['assets_amount']
        read_only_fields = [
            'key', 'assets_amount', 'org_id',
        ]

    def validate_value(self, data):
        instance = self.instance if self.instance else Node.root()
        children = instance.parent.get_children()
        children_values = [node.value for node in children if node != instance]
        if data in children_values:
            raise serializers.ValidationError(
                _('The same level node name cannot be the same')
            )
        return data


class NodeAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Node
        fields = ['assets']


class NodeAddChildrenSerializer(serializers.Serializer):
    nodes = serializers.ListField()

