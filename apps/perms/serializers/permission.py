# -*- coding: utf-8 -*-
#

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from assets.models import Asset, Node
from common.serializers.fields import BitChoicesField, ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import ActionChoices, AssetPermission
from users.models import User, UserGroup

__all__ = ["AssetPermissionSerializer", "ActionChoicesField"]


class ActionChoicesField(BitChoicesField):
    def __init__(self, **kwargs):
        super().__init__(choice_cls=ActionChoices, **kwargs)


class AssetPermissionSerializer(BulkOrgResourceModelSerializer):
    users = ObjectRelatedField(queryset=User.objects, many=True, required=False, label=_('User'))
    user_groups = ObjectRelatedField(
        queryset=UserGroup.objects, many=True, required=False, label=_('User group')
    )
    assets = ObjectRelatedField(queryset=Asset.objects, many=True, required=False, label=_('Asset'))
    nodes = ObjectRelatedField(queryset=Node.objects, many=True, required=False, label=_('Node'))
    actions = ActionChoicesField(required=False, allow_null=True, label=_("Actions"))
    is_valid = serializers.BooleanField(read_only=True, label=_("Is valid"))
    is_expired = serializers.BooleanField(read_only=True, label=_("Is expired"))
    accounts = serializers.ListField(label=_("Accounts"), required=False)

    class Meta:
        model = AssetPermission
        fields_mini = ["id", "name"]
        fields_generic = [
            "accounts",
            "actions",
            "created_by",
            "date_created",
            "date_start",
            "date_expired",
            "is_active",
            "is_expired",
            "is_valid",
            "comment",
            "from_ticket",
        ]
        fields_small = fields_mini + fields_generic
        fields_m2m = [
            "users",
            "user_groups",
            "assets",
            "nodes",
        ]
        fields = fields_mini + fields_m2m + fields_generic
        read_only_fields = ["created_by", "date_created", "from_ticket"]
        extra_kwargs = {
            "actions": {"label": _("Actions")},
            "is_expired": {"label": _("Is expired")},
            "is_valid": {"label": _("Is valid")},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_actions_field()

    def set_actions_field(self):
        actions = self.fields.get("actions")
        if not actions:
            return
        actions.default = list(actions.choices.keys())

    @staticmethod
    def validate_accounts(accounts):
        return list(set(accounts))

    @classmethod
    def setup_eager_loading(cls, queryset):
        """Perform necessary eager loading of data."""
        queryset = queryset.prefetch_related(
            "users",
            "user_groups",
            "assets",
            "nodes",
        )
        return queryset

    @staticmethod
    def perform_display_create(instance, **kwargs):
        # 用户
        users_to_set = User.objects.filter(
            Q(name__in=kwargs.get("users_display"))
            | Q(username__in=kwargs.get("users_display"))
        ).distinct()
        instance.users.add(*users_to_set)
        # 用户组
        user_groups_to_set = UserGroup.objects.filter(
            name__in=kwargs.get("user_groups_display")
        ).distinct()
        instance.user_groups.add(*user_groups_to_set)
        # 资产
        assets_to_set = Asset.objects.filter(
            Q(address__in=kwargs.get("assets_display"))
            | Q(name__in=kwargs.get("assets_display"))
        ).distinct()
        instance.assets.add(*assets_to_set)
        # 节点
        nodes_to_set = Node.objects.filter(
            full_value__in=kwargs.get("nodes_display")
        ).distinct()
        instance.nodes.add(*nodes_to_set)

    def create(self, validated_data):
        display = {
            "users_display": validated_data.pop("users_display", ""),
            "user_groups_display": validated_data.pop("user_groups_display", ""),
            "assets_display": validated_data.pop("assets_display", ""),
            "nodes_display": validated_data.pop("nodes_display", ""),
        }
        instance = super().create(validated_data)
        self.perform_display_create(instance, **display)
        return instance
