# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from assets.models import Node, Asset, Platform, Account
from perms.serializers.permission import ActionsField

__all__ = [
    'NodeGrantedSerializer',
    'AssetGrantedSerializer',
    'ActionsSerializer',
    'AccountsGrantedSerializer'
]


class AssetGrantedSerializer(serializers.ModelSerializer):
    """ 被授权资产的数据结构 """
    platform = serializers.SlugRelatedField(
        slug_field='name', queryset=Platform.objects.all(), label=_("Platform")
    )

    class Meta:
        model = Asset
        only_fields = [
            "id", "name", "ip", "protocols", 'domain',
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


class AccountsGrantedSerializer(serializers.ModelSerializer):
    """ 授权的账号序列类 """

    # Todo: 添加前端登录逻辑中需要的一些字段，比如：是否需要手动输入密码
    # need_manual = serializers.BooleanField(label=_('Need manual input'))

    class Meta:
        model = Account
        fields = ['id', 'name', 'username']
        read_only_fields = fields
