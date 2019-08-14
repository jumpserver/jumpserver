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
    name = serializers.ReadOnlyField(source='value')
    full_value = serializers.SerializerMethodField(label=_("Full value"))

    class Meta:
        model = Node
        only_fields = ['id', 'key', 'value', 'org_id']
        fields = only_fields + ['name', 'full_value']
        read_only_fields = [
            'key', 'name', 'full_value', 'org_id',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = Node.tree()

    def get_full_value(self, obj):
        return self.tree.get_node_full_tag(obj.key)

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

