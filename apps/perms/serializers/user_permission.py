# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from assets.models import Node, SystemUser
from assets.serializers import AssetSerializer

from .asset_permission import ActionsField

__all__ = [
    'AssetPermissionNodeSerializer', 'GrantedNodeSerializer',
    'NodeGrantedSerializer', 'AssetGrantedSerializer',
    'ActionsSerializer',
]


class AssetSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的资产系统用户的数据结构，这个和AssetSerializer不同，字段少
    """
    actions = ActionsField(read_only=True)

    class Meta:
        model = SystemUser
        fields = (
            'id', 'name', 'username', 'priority', "actions",
            'protocol', 'login_mode',
        )


class AssetGrantedSerializer(AssetSerializer):
    """
    被授权资产的数据结构
    """
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    system_users_join = serializers.SerializerMethodField()

    @staticmethod
    def get_system_users_join(obj):
        system_users = [s.username for s in obj.system_users_granted]
        return ', '.join(system_users)

    def get_field_names(self, declared_fields, info):
        fields = (
            "id", "hostname", "ip", "protocols",
            "system_users_granted", "is_active", "system_users_join", "os",
            'domain', "platform", "comment", "org_id", "org_name",
        )
        return fields


class AssetPermissionNodeSerializer(serializers.ModelSerializer):
    asset = AssetGrantedSerializer(required=False)
    assets_amount = serializers.SerializerMethodField()

    tree_id = serializers.SerializerMethodField()
    tree_parent = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'key', 'value', 'asset', 'is_node', 'org_id',
            'tree_id', 'tree_parent', 'assets_amount',
        ]

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets_amount

    @staticmethod
    def get_tree_id(obj):
        return obj.key

    @staticmethod
    def get_tree_parent(obj):
        return obj.parent_key


class NodeGrantedSerializer(serializers.ModelSerializer):
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


class GrantedNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value',
        ]


class ActionsSerializer(serializers.Serializer):
    actions = ActionsField(read_only=True)
