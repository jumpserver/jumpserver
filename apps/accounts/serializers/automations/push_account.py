from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.db import models

from common.serializers.fields import LabeledChoiceField, TreeChoicesField
from common.db.fields import TreeChoices
from accounts.models import PushAccountAutomation
from .change_secret import (
    ChangeSecretAutomationSerializer, ChangeSecretUpdateAssetSerializer,
    ChangeSecretUpdateNodeSerializer
)


class TriggerChoice(models.TextChoices, TreeChoices):
    # 当资产创建时，直接创建账号，如果是动态账号，需要从授权中查询该资产被授权过的用户，已用户用户名为账号，创建
    on_asset_create = 'on_asset_create', _('On asset create')
    # 授权变化包含，用户加入授权，用户组加入授权，资产加入授权，节点加入授权，账号变化
    # 当添加用户到授权时，查询所有同名账号 automation, 把本授权上的用户 (用户组), 创建到本授权的资产(节点)上
    on_perm_add_user = 'on_perm_add_user', _('On perm add user')
    # 当添加用户组到授权时，查询所有同名账号 automation, 把本授权上的用户 (用户组), 创建到本授权的资产(节点)上
    on_perm_add_user_group = 'on_perm_add_user_group', _('On perm add user group')
    # 当添加资产到授权时，查询授权的所有账号 automation, 创建到本授权的资产上
    on_perm_add_asset = 'on_perm_add_asset', _('On perm add asset')
    # 当添加节点到授权时，查询授权的所有账号 automation, 创建到本授权的节点的资产上
    on_perm_add_node = 'on_perm_add_node', _('On perm add node')
    # 当授权的账号变化时，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_perm_add_account = 'on_perm_add_account', _('On perm add account')
    # 当资产添加到节点时，查询节点的授权规则，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_asset_join_node = 'on_asset_join_node', _('On asset join node')
    # 当用户加入到用户组时，查询用户组的授权规则，查询授权的所有账号 automation, 创建到本授权的资产(节点)上
    on_user_join_group = 'on_user_join_group', _('On user join group')

    @classmethod
    def branches(cls):
        # 和用户和用户组相关的都是动态账号
        #
        return [
            cls.on_asset_create,
            (_("On perm change"), [
                cls.on_perm_add_user,
                cls.on_perm_add_user_group,
                cls.on_perm_add_asset,
                cls.on_perm_add_node,
                cls.on_perm_add_account,
            ]),
            (_("Inherit from group or node"), [
                cls.on_asset_join_node,
                cls.on_user_join_group,
            ])
        ]


class ActionChoice(models.TextChoices):
    create_and_push = 'create_and_push', _('Create and push')
    only_create = 'only_create', _('Only create')


class PushAccountAutomationSerializer(ChangeSecretAutomationSerializer):
    dynamic_username = serializers.BooleanField(label=_('Dynamic username'), default=False)
    triggers = TreeChoicesField(
        choice_cls=TriggerChoice, label=_('Triggers'),
        default=TriggerChoice.all(),
    )
    action = LabeledChoiceField(
        choices=ActionChoice.choices, label=_('Action'),
        default=ActionChoice.create_and_push
    )

    class Meta(ChangeSecretAutomationSerializer.Meta):
        model = PushAccountAutomation
        fields = ChangeSecretAutomationSerializer.Meta.fields + [
            'dynamic_username', 'triggers', 'action'
        ]

    def validate_username(self, value):
        if self.initial_data.get('dynamic_username'):
            value = '@USER'
        queryset = self.Meta.model.objects.filter(username=value)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError(_('Username already exists'))
        return value

    def validate_dynamic_username(self, value):
        if not value:
            return value
        queryset = self.Meta.model.objects.filter(username='@USER')
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError(_('Dynamic username already exists'))
        return value

    def validate_triggers(self, value):
        # Now triggers readonly, set all
        return TriggerChoice.all()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        excludes = [
            'recipients', 'is_periodic', 'interval', 'crontab',
            'periodic_display', 'assets', 'nodes'
        ]
        fields = [f for f in fields if f not in excludes]
        fields[fields.index('accounts')] = 'username'
        return fields


class PushAccountUpdateAssetSerializer(ChangeSecretUpdateAssetSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateAssetSerializer.Meta.fields


class PushAccountUpdateNodeSerializer(ChangeSecretUpdateNodeSerializer):
    class Meta:
        model = PushAccountAutomation
        fields = ChangeSecretUpdateNodeSerializer.Meta.fields
