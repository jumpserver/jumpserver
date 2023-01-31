# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.const import Category, AllTypes
from assets.models import Node, Asset, Platform
from accounts.models import Account
from assets.serializers.asset.common import AssetProtocolsSerializer
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from perms.serializers.permission import ActionChoicesField
from orgs.mixins.serializers import OrgResourceModelSerializerMixin

__all__ = [
    'NodePermedSerializer', 'AssetPermedSerializer',
    'AccountsPermedSerializer'
]


class AssetPermedSerializer(OrgResourceModelSerializerMixin):
    """ 被授权资产的数据结构 """
    platform = ObjectRelatedField(required=False, queryset=Platform.objects, label=_('Platform'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))
    domain = ObjectRelatedField(required=False, queryset=Node.objects, label=_('Domain'))

    class Meta:
        model = Asset
        only_fields = [
            "id", "name", "address", 'domain', 'platform',
            "comment", "org_id", "is_active",
        ]
        fields = only_fields + ['protocols', 'category', 'type', 'specific'] + ['org_name']
        read_only_fields = fields


class NodePermedSerializer(serializers.ModelSerializer):
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
        fields = [
            'alias', 'name', 'username', 'has_username',
            'has_secret', 'secret_type', 'actions'
        ]
        read_only_fields = fields
