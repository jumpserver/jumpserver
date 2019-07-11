# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from assets.models import Node, SystemUser, Asset

from .asset_permission import ActionsField

__all__ = [
    'AssetPermissionNodeSerializer', 'GrantedNodeSerializer',
    'NodeGrantedSerializer', 'AssetGrantedSerializer',
    'ActionsSerializer', 'AssetSystemUserSerializer',
]


class AssetSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的资产系统用户的数据结构，这个和AssetSerializer不同，字段少
    """
    actions = ActionsField(read_only=True)

    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority',
            'protocol', 'login_mode',
        )
        fields = list(only_fields) + ["actions"]


class AssetGrantedSerializer(serializers.ModelSerializer):
    """
    被授权资产的数据结构
    """
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    system_users_join = serializers.SerializerMethodField()
    system_users_only_fields = AssetSystemUserSerializer.Meta.only_fields

    class Meta:
        model = Asset
        only_fields = [
            "id", "hostname", "ip", "protocols", "os", 'domain',
            "platform", "org_id",
        ]
        fields = only_fields + ['system_users_granted', 'system_users_join', "org_name"]

    @staticmethod
    def get_system_users_join(obj):
        system_users = [s.username for s in obj.system_users_granted]
        return ', '.join(system_users)


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
    assets_amount = serializers.ReadOnlyField()
    parent = serializers.SerializerMethodField()
    name = serializers.ReadOnlyField(source='value')

    assets_only_fields = AssetGrantedSerializer.Meta.only_fields
    system_users_only_fields = AssetGrantedSerializer.system_users_only_fields

    class Meta:
        model = Node
        only_fields = ['id', 'key', 'value', "org_id"]
        fields = only_fields + [
            'name', 'parent', 'assets_granted', 'assets_amount',
        ]

    @staticmethod
    def get_parent(obj):
        return obj.parent_key


class GrantedNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value',
        ]


class ActionsSerializer(serializers.Serializer):
    actions = ActionsField(read_only=True)
