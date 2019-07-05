# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from assets.models import Node, SystemUser
from assets.serializers import AssetSerializer

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


class AssetGrantedSerializer(AssetSerializer):
    """
    被授权资产的数据结构
    """
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    system_users_join = serializers.SerializerMethodField()

    only_fields = (
        "id", "hostname", "ip", "protocols", "is_active", "os", 'domain',
        "platform", "comment", "org_id",
    )
    system_user_only_field = AssetSystemUserSerializer.Meta.only_fields

    @staticmethod
    def get_system_users_join(obj):
        system_users = [s.username for s in obj.system_users_granted]
        return ', '.join(system_users)

    def get_field_names(self, declared_fields, info):
        fields = [i for i in self.only_fields]
        fields.extend(['org_name', 'system_users_granted', 'system_users_join'])
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
