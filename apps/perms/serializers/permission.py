# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from rest_framework.fields import empty
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from common.drf.fields import ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import Asset, Node
from users.models import User, UserGroup
from perms.models import AssetPermission, Action

__all__ = ['AssetPermissionSerializer', 'ActionsField']


class ActionsField(serializers.MultipleChoiceField):
    def __init__(self, **kwargs):
        kwargs['choices'] = Action.CHOICES
        super().__init__(**kwargs)

    def run_validation(self, data=empty):
        data = super(ActionsField, self).run_validation(data)
        if isinstance(data, list):
            data = Action.choices_to_value(value=data)
        return data

    def to_representation(self, value):
        return Action.value_to_choices(value)

    def to_internal_value(self, data):
        if not self.allow_empty and not data:
            self.fail('empty')
        if not data:
            return data
        return Action.choices_to_value(data)


class ActionsDisplayField(ActionsField):
    def to_representation(self, value):
        values = super().to_representation(value)
        choices = dict(Action.CHOICES)
        return [choices.get(i) for i in values]


class AssetPermissionSerializer(BulkOrgResourceModelSerializer):
    users = ObjectRelatedField(queryset=User.objects, many=True, required=False)
    user_groups = ObjectRelatedField(queryset=UserGroup.objects, many=True, required=False)
    assets = ObjectRelatedField(queryset=Asset.objects, many=True, required=False)
    nodes = ObjectRelatedField(queryset=Node.objects, many=True, required=False)
    actions = ActionsField(required=False, allow_null=True, label=_("Actions"))
    is_valid = serializers.BooleanField(read_only=True, label=_("Is valid"))
    is_expired = serializers.BooleanField(read_only=True, label=_('Is expired'))

    class Meta:
        model = AssetPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'accounts', 'is_active', 'is_expired', 'is_valid',
            'actions', 'created_by', 'date_created', 'date_expired',
            'date_start', 'comment', 'from_ticket'
        ]
        fields_m2m = [
            'users', 'user_groups',  'assets', 'nodes',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created', 'from_ticket']
        extra_kwargs = {
            'actions': {'label': _('Actions')},
            'is_expired': {'label': _('Is expired')},
            'is_valid': {'label': _('Is valid')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_actions_field()

    def set_actions_field(self):
        actions = self.fields.get('actions')
        if not actions:
            return
        choices = actions._choices
        actions._choices = choices
        actions.default = list(choices.keys())

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
            Q(address__in=kwargs.get('assets_display')) |
            Q(name__in=kwargs.get('assets_display'))
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

