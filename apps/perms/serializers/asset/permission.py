# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from perms.models import AssetPermission, Action
from assets.models import Asset, Node
from users.models import User, UserGroup
from ..base import ActionsField, BasePermissionSerializer

__all__ = ['AssetPermissionSerializer']


class AssetPermissionSerializer(BasePermissionSerializer):
    actions = ActionsField(required=False, allow_null=True, label=_("Actions"))
    is_valid = serializers.BooleanField(read_only=True, label=_("Is valid"))
    is_expired = serializers.BooleanField(read_only=True, label=_('Is expired'))
    users_display = serializers.ListField(child=serializers.CharField(), label=_('Users display'), required=False)
    user_groups_display = serializers.ListField(child=serializers.CharField(), label=_('User groups display'), required=False)
    assets_display = serializers.ListField(child=serializers.CharField(), label=_('Assets display'), required=False)
    nodes_display = serializers.ListField(child=serializers.CharField(), label=_('Nodes display'), required=False)

    class Meta:
        model = AssetPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'is_active', 'is_expired', 'is_valid', 'actions',
            'created_by', 'date_created', 'date_expired',
            'date_start', 'comment', 'from_ticket'
        ]
        fields_m2m = [
            'users', 'users_display', 'user_groups', 'user_groups_display', 'assets',
            'assets_display', 'nodes', 'nodes_display', 'accounts',
            'users_amount', 'user_groups_amount', 'assets_amount',
            'nodes_amount',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created', 'from_ticket']
        extra_kwargs = {
            'is_expired': {'label': _('Is expired')},
            'is_valid': {'label': _('Is valid')},
            'actions': {'label': _('Actions')},
            'users_amount': {'label': _('Users amount')},
            'user_groups_amount': {'label': _('User groups amount')},
            'assets_amount': {'label': _('Assets amount')},
            'nodes_amount': {'label': _('Nodes amount')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            'users', 'user_groups', 'assets', 'nodes',
        )
        return queryset

    @staticmethod
    def perform_display_create(instance, **kwargs):
        # 用户
        users_to_set = User.objects.filter(
            Q(name__in=kwargs.get('users_display')) |
            Q(username__in=kwargs.get('users_display'))
        ).distinct()
        instance.users.add(*users_to_set)
        # 用户组
        user_groups_to_set = UserGroup.objects.filter(
            name__in=kwargs.get('user_groups_display')
        ).distinct()
        instance.user_groups.add(*user_groups_to_set)
        # 资产
        assets_to_set = Asset.objects.filter(
            Q(ip__in=kwargs.get('assets_display')) |
            Q(hostname__in=kwargs.get('assets_display'))
        ).distinct()
        instance.assets.add(*assets_to_set)
        # 节点
        nodes_to_set = Node.objects.filter(
            full_value__in=kwargs.get('nodes_display')
        ).distinct()
        instance.nodes.add(*nodes_to_set)

    def create(self, validated_data):
        display = {
            'users_display': validated_data.pop('users_display', ''),
            'user_groups_display': validated_data.pop('user_groups_display', ''),
            'assets_display': validated_data.pop('assets_display', ''),
            'nodes_display': validated_data.pop('nodes_display', '')
        }
        instance = super().create(validated_data)
        self.perform_display_create(instance, **display)
        return instance

