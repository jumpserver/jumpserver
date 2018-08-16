# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkSerializerMixin
from ..models import Asset, Node
from .asset import AssetGrantedSerializer


__all__ = [
    'NodeSerializer', "NodeGrantedSerializer", "NodeAddChildrenSerializer",
    "NodeAssetsSerializer",
]


class NodeGrantedSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    授权资产组
    """
    assets_granted = AssetGrantedSerializer(many=True, read_only=True)
    assets_amount = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'key', 'name', 'value', 'parent',
            'assets_granted', 'assets_amount', 'org_id',
        ]

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.assets_granted)

    @staticmethod
    def get_name(obj):
        return obj.name

    @staticmethod
    def get_parent(obj):
        return obj.parent.id


class NodeSerializer(serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    tree_id = serializers.SerializerMethodField()
    tree_parent = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'key', 'value', 'assets_amount',
            'is_node', 'org_id', 'tree_id', 'tree_parent',
        ]
        list_serializer_class = BulkListSerializer

    def validate(self, data):
        value = data.get('value')
        instance = self.instance if self.instance else Node.root()
        children = instance.parent.get_children().exclude(key=instance.key)
        values = [child.value for child in children]
        if value in values:
            raise serializers.ValidationError(
                'The same level node name cannot be the same'
            )
        return data

    @staticmethod
    def get_assets_amount(obj):
        return obj.get_all_assets().count()

    @staticmethod
    def get_tree_id(obj):
        return obj.key

    @staticmethod
    def get_tree_parent(obj):
        return obj.parent_key

    def get_fields(self):
        fields = super().get_fields()
        field = fields["key"]
        field.required = False
        return fields


class NodeAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset = Asset.objects.all())

    class Meta:
        model = Node
        fields = ['assets']


class NodeAddChildrenSerializer(serializers.Serializer):
    nodes = serializers.ListField()
