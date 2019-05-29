# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from common.fields import StringManyToManyField
from perms.models import AssetPermission, Action
from assets.models import Node, Asset, SystemUser
from assets.serializers import AssetGrantedSerializer

__all__ = [
    'AssetPermissionCreateUpdateSerializer', 'AssetPermissionListSerializer',
    'AssetPermissionUpdateUserSerializer', 'AssetPermissionUpdateAssetSerializer',
    'AssetPermissionNodeSerializer', 'GrantedNodeSerializer',
    'GrantedAssetSerializer', 'GrantedSystemUserSerializer',
    'ActionSerializer', 'NodeGrantedSerializer',
]


class ActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Action
        fields = '__all__'


class AssetPermissionCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPermission
        exclude = ('created_by', 'date_created')


class AssetPermissionListSerializer(serializers.ModelSerializer):
    users = StringManyToManyField(many=True, read_only=True)
    user_groups = StringManyToManyField(many=True, read_only=True)
    assets = StringManyToManyField(many=True, read_only=True)
    nodes = StringManyToManyField(many=True, read_only=True)
    system_users = StringManyToManyField(many=True, read_only=True)
    actions = StringManyToManyField(many=True, read_only=True)
    is_valid = serializers.BooleanField()
    is_expired = serializers.BooleanField()

    class Meta:
        model = AssetPermission
        fields = '__all__'


class AssetPermissionUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'users']


class AssetPermissionUpdateAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'assets']


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


class GrantedAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id', 'hostname', 'ip', 'port', 'protocol', 'platform',
            'domain', 'is_active', 'comment'
        ]


class GrantedSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = [
            'id', 'name', 'username', 'protocol', 'priority',
            'login_mode', 'comment'
        ]
