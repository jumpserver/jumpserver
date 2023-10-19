# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Asset, Node

__all__ = [
    'NodeSerializer', "NodeAddChildrenSerializer",
    "NodeAssetsSerializer", "NodeTaskSerializer",
]


class NodeSerializer(BulkOrgResourceModelSerializer):
    name = serializers.ReadOnlyField(source='value')
    value = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, label=_("value")
    )
    full_value = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, label=_("Full value")
    )

    class Meta:
        model = Node
        only_fields = ['id', 'key', 'value', 'org_id']
        fields = only_fields + ['name', 'full_value']
        read_only_fields = ['key', 'org_id']

    def validate_value(self, data):
        if '/' in data:
            error = _("Can't contains: " + "/")
            raise serializers.ValidationError(error)
        view = self.context['view']
        instance = self.instance or getattr(view, 'instance', None)
        if instance:
            siblings = instance.get_siblings()
        else:
            instance = Node.org_root()
            siblings = instance.get_children()
        if siblings.filter(value=data):
            raise serializers.ValidationError(
                _('The same level node name cannot be the same')
            )
        return data

    def create(self, validated_data):
        full_value = validated_data.get('full_value')

        # 直接多层级创建
        if full_value:
            node = Node.create_node_by_full_value(full_value)
        # 根据 value 在 root 下创建
        else:
            key = Node.org_root().get_next_child_key()
            validated_data['key'] = key
            node = Node.objects.create(**validated_data)
        return node


class NodeAssetsSerializer(BulkOrgResourceModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Asset.objects
    )

    class Meta:
        model = Node
        fields = ['assets']


class NodeAddChildrenSerializer(serializers.Serializer):
    nodes = serializers.ListField()


class NodeTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('refresh', 'refresh'),
        ('test', 'test'),
        ('refresh_cache', 'refresh_cache'),
    )
    task = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
