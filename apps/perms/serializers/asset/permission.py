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
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = AssetPermission
        mini_fields = ['id', 'name']
        small_fields = mini_fields + [
            'is_active', 'is_expired', 'is_valid', 'actions',
            'created_by', 'date_created', 'date_expired',
            'date_start', 'comment'
        ]
        m2m_fields = [
            'users', 'user_groups', 'assets', 'nodes', 'system_users',
            'users_amount', 'user_groups_amount', 'assets_amount',
            'nodes_amount', 'system_users_amount',
        ]
        fields = small_fields + m2m_fields
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
