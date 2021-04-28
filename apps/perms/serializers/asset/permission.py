# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Prefetch, Q

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import AssetPermission, Action
from assets.models import Asset, Node, SystemUser
from users.models import User, UserGroup

__all__ = [
    'AssetPermissionSerializer',
    'ActionsField',
]


class ActionsField(serializers.MultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['choices'] = Action.CHOICES
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        return Action.value_to_choices(value)

    def to_internal_value(self, data):
        if data is None:
            return data
        return Action.choices_to_value(data)


class ActionsDisplayField(ActionsField):
    def to_representation(self, value):
        values = super().to_representation(value)
        choices = dict(Action.CHOICES)
        return [choices.get(i) for i in values]


class AssetPermissionSerializer(BulkOrgResourceModelSerializer):
    actions = ActionsField(required=False, allow_null=True)
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True, label=_('Is expired'))
    users_display = serializers.ListField(child=serializers.CharField(), label=_('Users name'), required=False)
    user_groups_display = serializers.ListField(child=serializers.CharField(), label=_('User groups name'), required=False)
    assets_display = serializers.ListField(child=serializers.CharField(), label=_('Assets name'), required=False)
    nodes_display = serializers.ListField(child=serializers.CharField(), label=_('Nodes name'), required=False)
    system_users_display = serializers.ListField(child=serializers.CharField(), label=_('System users name'), required=False)

    class Meta:
        model = AssetPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'is_active', 'is_expired', 'is_valid', 'actions',
            'created_by', 'date_created', 'date_expired',
            'date_start', 'comment'
        ]
        fields_m2m = [
            'users', 'users_display', 'user_groups', 'user_groups_display', 'assets', 'assets_display',
            'nodes', 'nodes_display', 'system_users', 'system_users_display',
            'users_amount', 'user_groups_amount', 'assets_amount',
            'nodes_amount', 'system_users_amount',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']
        extra_kwargs = {
            'is_expired': {'label': _('Is expired')},
            'is_valid': {'label': _('Is valid')},
            'actions': {'label': _('Actions')},
            'users_amount': {'label': _('Users amount')},
            'user_groups_amount': {'label': _('User groups amount')},
            'assets_amount': {'label': _('Assets amount')},
            'nodes_amount': {'label': _('Nodes amount')},
            'system_users_amount': {'label': _('System users amount')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            Prefetch('system_users', queryset=SystemUser.objects.only('id')),
            Prefetch('user_groups', queryset=UserGroup.objects.only('id')),
            Prefetch('users', queryset=User.objects.only('id')),
            Prefetch('assets', queryset=Asset.objects.only('id')),
            Prefetch('nodes', queryset=Node.objects.only('id'))
        )
        return queryset

    def to_internal_value(self, data):
        # 系统用户是必填项
        for i in range(len(data['system_users_display'])):
            system_user = SystemUser.objects.filter(name=data['system_users_display'][i]).first()
            if system_user and system_user.id not in data['system_users']:
                data['system_users'].append(system_user.id)
        return super().to_internal_value(data)


    def perform_display_create(self, instance, users_display, user_groups_display, assets_display, nodes_display):
        # 用户
        users_to_set = []
        for name in users_display:
            user = User.objects.filter(Q(name=name) | Q(username=name)).first()
            if user:
                users_to_set.append(user)
        instance.users.set(users_to_set)
        # 用户组
        user_groups_to_set = []
        for name in user_groups_display:
            user_group = UserGroup.objects.filter(name=name).first()
            if user_group:
                user_groups_to_set.append(user_group)
        instance.user_groups.set(user_groups_to_set)
        # 资产
        assets_to_set = []
        for name in assets_display:
            asset = Asset.objects.filter(Q(ip=name) | Q(hostname=name)).first()
            if asset:
                assets_to_set.append(asset)
        instance.assets.set(assets_to_set)
        # 节点
        nodes_to_set = []
        for full_value in nodes_display:
            node = Node.objects.filter(full_value=full_value).first()
            if node:
                nodes_to_set.append(node)
            else:
                node = Node.create_node_by_full_value(full_value)
            nodes_to_set.append(node)
        instance.nodes.set(nodes_to_set)

    def create(self, validated_data):
        users_display = validated_data.pop('users_display', '')
        user_groups_display = validated_data.pop('user_groups_display', '')
        assets_display = validated_data.pop('assets_display', '')
        nodes_display = validated_data.pop('nodes_display', '')
        system_users_display = validated_data.pop('system_users_display', '')
        instance = super().create(validated_data)
        self.perform_display_create(instance, users_display, user_groups_display, assets_display, nodes_display)
        return instance
