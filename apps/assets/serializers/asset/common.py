# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from ...models import Asset, Node, Platform, SystemUser, Protocol, Label
from ..mixin import CategoryDisplayMixin
from ..account import AccountSerializer

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer',
]


class AssetProtocolsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['id', 'name', 'port']


class AssetLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'value']


class AssetSerializer(CategoryDisplayMixin, OrgResourceModelSerializerMixin):
    domain_display = serializers.ReadOnlyField(source='domain.name', label=_('Domain name'))
    nodes_display = serializers.ListField(
        child=serializers.CharField(), label=_('Nodes name'), required=False
    )
    labels_display = serializers.ListField(
        child=serializers.CharField(), label=_('Labels name'),
        required=False, read_only=True
    )
    labels = AssetLabelSerializer(many=True, required=False)
    platform_display = serializers.SlugField(
        source='platform.name', label=_("Platform display"), read_only=True
    )
    accounts = AccountSerializer(many=True, write_only=True, required=False)
    protocols = AssetProtocolsSerializer(many=True)

    """
    资产的数据结构
    """

    class Meta:
        model = Asset
        fields_mini = [
            'id', 'hostname', 'ip',
        ]
        fields_small = fields_mini + [
            'is_active', 'number', 'comment',
        ]
        fields_fk = [
            'domain', 'domain_display', 'platform', 'platform', 'platform_display',
        ]
        fields_m2m = [
            'nodes', 'nodes_display', 'labels', 'labels_display', 'accounts', 'protocols',
        ]
        read_only_fields = [
            'category', 'category_display', 'type', 'type_display',
            'connectivity', 'date_verified', 'created_by', 'date_created',
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        extra_kwargs = {
            'hostname': {'label': _("Name")},
            'ip': {'label': _('IP/Host')},
            'protocol': {'write_only': True},
            'port': {'write_only': True},
            'admin_user_display': {'label': _('Admin user display'), 'read_only': True},
        }

    def __init__(self, *args, **kwargs):
        data = kwargs.get('data', {})
        self.accounts_data = data.pop('accounts', [])
        super().__init__(*args, **kwargs)

    def get_fields(self):
        fields = super().get_fields()

        admin_user_field = fields.get('admin_user')
        # 因为 mixin 中对 fields 有处理，可能不需要返回 admin_user
        if admin_user_field:
            admin_user_field.queryset = SystemUser.objects.filter(type=SystemUser.Type.admin)
        return fields

    def validate_type(self, value):
        print(self.initial_data)
        return value

    def validate_category(self, value):
        return value

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('domain', 'platform', 'protocols')
        queryset = queryset.prefetch_related('nodes', 'labels')
        return queryset

    def perform_nodes_display_create(self, instance, nodes_display):
        if not nodes_display:
            return
        nodes_to_set = []
        for full_value in nodes_display:
            node = Node.objects.filter(full_value=full_value).first()
            if node:
                nodes_to_set.append(node)
            else:
                node = Node.create_node_by_full_value(full_value)
            nodes_to_set.append(node)
        instance.nodes.set(nodes_to_set)

    @staticmethod
    def add_accounts(instance, accounts_data):
        for data in accounts_data:
            data['asset'] = instance.id
        serializer = AccountSerializer(data=accounts_data, many=True)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            raise serializers.ValidationError({'accounts': e})
        serializer.save()

    def create(self, validated_data):
        self.compatible_with_old_protocol(validated_data)
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().create(validated_data)
        if self.accounts_data:
            self.add_accounts(instance, self.accounts_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance

    def update(self, instance, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        self.compatible_with_old_protocol(validated_data)
        instance = super().update(instance, validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance


class MiniAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = AssetSerializer.Meta.fields_mini


class AssetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id', 'hostname', 'ip', 'port',
            'connectivity', 'date_verified'
        ]


class AssetsTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('refresh', 'refresh'),
        ('test', 'test'),
    )
    task = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    assets = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, allow_empty=True, many=True
    )


class AssetTaskSerializer(AssetsTaskSerializer):
    ACTION_CHOICES = tuple(list(AssetsTaskSerializer.ACTION_CHOICES) + [
        ('push_system_user', 'push_system_user'),
        ('test_system_user', 'test_system_user')
    ])
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, allow_empty=True, many=False
    )
    system_users = serializers.PrimaryKeyRelatedField(
        queryset=SystemUser.objects, required=False, allow_empty=True, many=True
    )
