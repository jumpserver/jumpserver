# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.const import Category, AllTypes
from assets.models import Node, Asset, Platform, Account
from assets.serializers.asset.common import AssetProtocolsSerializer
from common.drf.fields import ObjectRelatedField, LabeledChoiceField
from perms.serializers.permission import ActionChoicesField

__all__ = [
    'NodeGrantedSerializer', 'AssetGrantedSerializer',
    'AccountsPermedSerializer'
]


class AssetGrantedSerializer(serializers.ModelSerializer):
    """ 被授权资产的数据结构 """
    platform = ObjectRelatedField(required=False, queryset=Platform.objects, label=_('Platform'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))

    class Meta:
        model = Asset
        only_fields = [
            "id", "name", "address",
            'domain', 'platform',
            "comment", "org_id", "is_active",
        ]
        fields = only_fields + ['protocols', 'category', 'type'] + ['org_name']
        read_only_fields = fields


class NodeGrantedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Node
        fields = [
            'id', 'name', 'key', 'value', 'org_id', "assets_amount"
        ]
        read_only_fields = fields


class AccountsPermedSerializer(serializers.ModelSerializer):
    actions = ActionChoicesField(read_only=True)

    class Meta:
        model = Account
        fields = ['id', 'name', 'has_username', 'username',
                  'has_secret', 'secret_type', 'actions']
        read_only_fields = fields
