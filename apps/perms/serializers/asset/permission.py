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
        queryset = queryset.prefetch_related('users', 'user_groups', 'assets', 'nodes', 'system_users')
        return queryset

    def to_internal_value(self, data):
        if 'system_users_display' in data:
            # system_users_display 转化为 system_users
            system_users = data.get('system_users', [])
            system_users_display = data.pop('system_users_display')

            for name in system_users_display:
                system_user = SystemUser.objects.filter(name=name).first()
                if system_user and system_user.id not in system_users:
                    system_users.append(system_user.id)
            data['system_users'] = system_users

        return super().to_internal_value(data)

    def perform_display_create(self, instance, **kwargs):
        # 用户
        users_to_set = User.objects.filter(
            Q(name__in=kwargs.get('users_display')) | Q(username__in=kwargs.get('users_display'))
        ).distinct()
        instance.users.add(*users_to_set)
        # 用户组
        user_groups_to_set = UserGroup.objects.filter(name__in=kwargs.get('user_groups_display')).distinct()
        instance.user_groups.add(*user_groups_to_set)
        # 资产
        assets_to_set = Asset.objects.filter(
            Q(ip__in=kwargs.get('assets_display')) | Q(hostname__in=kwargs.get('assets_display'))
        ).distinct()
        instance.assets.add(*assets_to_set)
        # 节点
        nodes_to_set = Node.objects.filter(full_value__in=kwargs.get('nodes_display')).distinct()
        instance.nodes.add(*nodes_to_set)

    def create(self, validated_data):
        display = {
            'users_display' : validated_data.pop('users_display', ''),
            'user_groups_display' : validated_data.pop('user_groups_display', ''),
            'assets_display' : validated_data.pop('assets_display', ''),
            'nodes_display' : validated_data.pop('nodes_display', '')
        }
        instance = super().create(validated_data)
        self.perform_display_create(instance, **display)
        return instance

