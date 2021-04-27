# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Prefetch

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import AssetPermission, Action
from assets.models import Asset, Node, SystemUser
from users.models import User, UserGroup

__all__ = [
    'AssetPermissionSerializer',
    'ActionsField',
    'AssetPermissionDisplaySerializer'
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

    class Meta:
        model = AssetPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'is_active', 'is_expired', 'is_valid', 'actions',
            'created_by', 'date_created', 'date_expired',
            'date_start', 'comment'
        ]
        fields_m2m = [
            'users', 'user_groups', 'assets', 'nodes', 'system_users',
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

class AssetPermissionDisplaySerializer(AssetPermissionSerializer):
    users_display = serializers.ListSerializer(child=serializers.CharField(), source='users', label=_('Users name'),
                                               required=False)
    user_groups_display = serializers.ListSerializer(child=serializers.CharField(), source='user_groups',
                                                     label=_('User groups name'), required=False)
    assets_display = serializers.ListSerializer(child=serializers.CharField(), source='assets',
                                                label=_('Assets name'), required=False)
    nodes_display = serializers.ListSerializer(child=serializers.CharField(), source='nodes', label=_('Nodes name'),
                                               required=False)
    system_users_display = serializers.ListSerializer(child=serializers.CharField(), source='system_users',
                                                      label=_('System users name'), required=False)

    class Meta(AssetPermissionSerializer.Meta):
        fields = AssetPermissionSerializer.Meta.fields + [
            'users_display', 'user_groups_display', 'assets_display', 'nodes_display', 'system_users_display'
        ]

