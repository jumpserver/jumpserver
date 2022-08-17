# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import Node, Asset, Platform
from perms.serializers.base import ActionsField

__all__ = [
    'NodeGrantedSerializer',
    'AssetGrantedSerializer',
    'ActionsSerializer',
]


class AssetGrantedSerializer(serializers.ModelSerializer):
    """
    被授权资产的数据结构
    """
    platform = serializers.SlugRelatedField(
        slug_field='name', queryset=Platform.objects.all(), label=_("Platform")
    )

    class Meta:
        model = Asset
        only_fields = [
            "id", "name", "ip", "protocols", "os", 'domain',
            "platform", "comment", "org_id", "is_active"
        ]
        fields = only_fields + ['org_name']
        read_only_fields = fields


class NodeGrantedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value', 'org_id', "assets_amount"
        ]
        read_only_fields = fields


class ActionsSerializer(serializers.Serializer):
    actions = ActionsField(read_only=True)

