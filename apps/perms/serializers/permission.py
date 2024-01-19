# -*- coding: utf-8 -*-
#
from django.db.models import Q, Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import Source
from accounts.models import AccountTemplate, Account
from accounts.tasks import push_accounts_to_assets_task
from assets.models import Asset, Node
from common.serializers import ResourceLabelsMixin
from common.serializers.fields import BitChoicesField, ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import ActionChoices, AssetPermission
from users.models import User, UserGroup

__all__ = ["AssetPermissionSerializer", "ActionChoicesField", "AssetPermissionListSerializer"]


class ActionChoicesField(BitChoicesField):
    def __init__(self, **kwargs):
        super().__init__(choice_cls=ActionChoices, **kwargs)

    def to_file_representation(self, value):
        return [v['value'] for v in value]

    def to_file_internal_value(self, data):
        return data


class AssetPermissionSerializer(ResourceLabelsMixin, BulkOrgResourceModelSerializer):
    users = ObjectRelatedField(queryset=User.objects, many=True, required=False, label=_('User'))
    user_groups = ObjectRelatedField(
        queryset=UserGroup.objects, many=True, required=False, label=_('User group')
    )
    assets = ObjectRelatedField(queryset=Asset.objects, many=True, required=False, label=_('Asset'))
    nodes = ObjectRelatedField(queryset=Node.objects, many=True, required=False, label=_('Node'))
    actions = ActionChoicesField(required=False, allow_null=True, label=_("Actions"))
    is_valid = serializers.BooleanField(read_only=True, label=_("Is valid"))
    is_expired = serializers.BooleanField(read_only=True, label=_("Is expired"))
    accounts = serializers.ListField(label=_("Account"), required=False)
    protocols = serializers.ListField(label=_("Protocols"), required=False)

    template_accounts = AccountTemplate.objects.none()

    class Meta:
        model = AssetPermission
        fields_mini = ["id", "name"]
        fields_generic = [
            "accounts", "protocols", "actions", "created_by", "date_created",
            "date_start", "date_expired", "is_active", "is_expired",
            "is_valid", "comment", "from_ticket",
        ]
        fields_small = fields_mini + fields_generic
        fields_m2m = ["users", "user_groups", "assets", "nodes", "labels"]
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
    def get_all_assets(nodes, assets):
        node_asset_ids = Node.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        direct_asset_ids = [asset.id for asset in assets]
        asset_ids = set(direct_asset_ids + list(node_asset_ids))
        return Asset.objects.filter(id__in=asset_ids)

    def create_accounts(self, assets):
        need_create_accounts = []
        account_attribute = [
            'name', 'username', 'secret_type', 'secret',
            'privileged', 'is_active', 'org_id'
        ]
        for asset in assets:
            asset_exist_accounts = Account.objects.none()
            asset_exist_account_names = asset.accounts.values_list('name', flat=True)
            for template in self.template_accounts:
                asset_exist_accounts |= asset.accounts.filter(
                    username=template.username,
                    secret_type=template.secret_type,
                )
            username_secret_type_dict = asset_exist_accounts.values('username', 'secret_type')
            for template in self.template_accounts:
                condition = {
                    'username': template.username,
                    'secret_type': template.secret_type
                }
                if condition in username_secret_type_dict or \
                        template.name in asset_exist_account_names:
                    continue
                account_data = {key: getattr(template, key) for key in account_attribute}
                account_data['su_from'] = template.get_su_from_account(asset)
                account_data['source'] = Source.TEMPLATE
                account_data['source_id'] = str(template.id)
                need_create_accounts.append(Account(**{'asset_id': asset.id, **account_data}))
        return Account.objects.bulk_create(need_create_accounts)

    def create_and_push_account(self, nodes, assets):
        if not self.template_accounts:
            return
        assets = self.get_all_assets(nodes, assets)
        accounts = self.create_accounts(assets)
        account_ids = [str(account.id) for account in accounts]
        slice_count = 20
        for i in range(0, len(account_ids), slice_count):
            push_accounts_to_assets_task.delay(account_ids[i:i + slice_count])

    def validate_accounts(self, usernames):
        template_ids = []
        account_usernames = []
        for username in usernames:
            if username.startswith('%'):
                template_ids.append(username[1:])
            else:
                account_usernames.append(username)
        self.template_accounts = AccountTemplate.objects.filter(id__in=template_ids)
        template_usernames = list(self.template_accounts.values_list('username', flat=True))
        return list(set(account_usernames + template_usernames))

    @classmethod
    def setup_eager_loading(cls, queryset):
        """Perform necessary eager loading of data."""
        queryset = queryset.prefetch_related(
            "users", "user_groups", "assets", "nodes",
        ).prefetch_related('labels', 'labels__label')
        return queryset

    @staticmethod
    def perform_display_create(instance, **kwargs):
        # 用户
        users_to_set = User.objects.filter(
            Q(name__in=kwargs.get("users_display")) |
            Q(username__in=kwargs.get("users_display"))
        ).distinct()
        instance.users.add(*users_to_set)
        # 用户组
        user_groups_to_set = UserGroup.objects.filter(
            name__in=kwargs.get("user_groups_display")
        ).distinct()
        instance.user_groups.add(*user_groups_to_set)
        # 资产
        assets_to_set = Asset.objects.filter(
            Q(address__in=kwargs.get("assets_display")) |
            Q(name__in=kwargs.get("assets_display"))
        ).distinct()
        instance.assets.add(*assets_to_set)
        # 节点
        nodes_to_set = Node.objects.filter(
            full_value__in=kwargs.get("nodes_display")
        ).distinct()
        instance.nodes.add(*nodes_to_set)

    def validate(self, attrs):
        self.create_and_push_account(
            attrs.get("nodes", []),
            attrs.get("assets", [])
        )
        return super().validate(attrs)

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


class AssetPermissionListSerializer(AssetPermissionSerializer):
    users_amount = serializers.IntegerField(read_only=True, label=_("Users amount"))
    user_groups_amount = serializers.IntegerField(read_only=True, label=_("User groups amount"))
    assets_amount = serializers.IntegerField(read_only=True, label=_("Assets amount"))
    nodes_amount = serializers.IntegerField(read_only=True, label=_("Nodes amount"))

    class Meta(AssetPermissionSerializer.Meta):
        amount_fields = ["users_amount", "user_groups_amount", "assets_amount", "nodes_amount"]
        remove_fields = {"users", "assets", "nodes", "user_groups"}
        fields = list(set(AssetPermissionSerializer.Meta.fields + amount_fields) - remove_fields)

    @classmethod
    def setup_eager_loading(cls, queryset):
        """Perform necessary eager loading of data."""
        queryset = queryset \
            .prefetch_related('labels', 'labels__label') \
            .annotate(users_amount=Count("users", distinct=True),
                      user_groups_amount=Count("user_groups", distinct=True),
                      assets_amount=Count("assets", distinct=True),
                      nodes_amount=Count("nodes", distinct=True),
                      )
        return queryset
