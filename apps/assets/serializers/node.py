# -*- coding: utf-8 -*-
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkSerializerMixin
from ..models import Asset, Node
from .asset import AssetGrantedSerializer


class NodeGrantedSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    授权资产组
    """
    assets_granted = AssetGrantedSerializer(many=True, read_only=True)
    assets_amount = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'key', 'value', 'parent',
            'assets_granted', 'assets_amount',
        ]

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.assets_granted)

    @staticmethod
    def get_parent(obj):
        return obj.parent.id


class NodeSerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = ['id', 'key', 'value', 'parent']
        list_serializer_class = BulkListSerializer

    @staticmethod
    def get_parent(obj):
        return obj.parent.id

    def get_fields(self):
        fields = super().get_fields()
        field = fields["key"]
        field.required = False
        return fields


class NodeAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Node
        fields = ['assets']