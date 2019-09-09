# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import Node, SystemUser, Asset
from assets.serializers import ProtocolsField
from .asset_permission import ActionsField

__all__ = [
    'NodeGrantedSerializer',
    'AssetGrantedSerializer',
    'ActionsSerializer', 'AssetSystemUserSerializer',
    'RemoteAppSystemUserSerializer',
]


class AssetSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的资产系统用户的数据结构，这个和AssetSerializer不同，字段少
    """
    actions = ActionsField(read_only=True)

    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
        )
        fields = list(only_fields) + ["actions"]
        read_only_fields = fields


class RemoteAppSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        only_fields = (
            'id', 'name', 'username', 'priority', 'protocol', 'login_mode',
        )
        fields = list(only_fields)
        read_only_fields = fields


class AssetGrantedSerializer(serializers.ModelSerializer):
    """
    被授权资产的数据结构
    """
    protocols = ProtocolsField(label=_('Protocols'), required=False, read_only=True)

    class Meta:
        model = Asset
        only_fields = [
            "id", "hostname", "ip", "protocols", "os", 'domain',
            "platform", "comment", "org_id",
        ]
        fields = only_fields + ['org_name']
        read_only_fields = fields


class NodeGrantedSerializer(serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value', 'org_id', "assets_amount"
        ]
        read_only_fields = fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = self.context.get("tree")

    def get_assets_amount(self, obj):
        if not self.tree:
            return 0
        return self.tree.assets_amount(obj.key)


class ActionsSerializer(serializers.Serializer):
    actions = ActionsField(read_only=True)
