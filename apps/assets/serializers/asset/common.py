# -*- coding: utf-8 -*-
#

from django.db.models import F
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.fields import LabeledChoiceField, ObjectRelatedField
from common.drf.serializers import WritableNestedModelSerializer
from orgs.mixins.serializers import BulkOrgResourceSerializerMixin
from ..account import AccountSerializer
from ...const import Category, AllTypes
from ...models import Asset, Node, Platform, Label, Domain, Account, Protocol

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer', 'AssetProtocolsSerializer',
    'AssetDetailSerializer',
]


class AssetProtocolsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['id', 'name', 'port']


class AssetLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'value']
        extra_kwargs = {
            'name': {'required': False},
            'value': {'required': False}
        }


class AssetPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ['id', 'name']
        extra_kwargs = {
            'name': {'required': False}
        }


class AssetAccountSerializer(AccountSerializer):
    add_org_fields = False

    class Meta(AccountSerializer.Meta):
        fields_mini = [
            'id', 'name', 'username', 'privileged',
            'version', 'secret_type',
        ]
        fields_write_only = [
            'secret', 'push_now'
        ]
        fields = fields_mini + fields_write_only


class AssetSerializer(BulkOrgResourceSerializerMixin, WritableNestedModelSerializer):
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))
    domain = ObjectRelatedField(required=False, queryset=Domain.objects, label=_('Domain'), allow_null=True)
    platform = ObjectRelatedField(required=False, queryset=Platform.objects, label=_('Platform'))
    nodes = ObjectRelatedField(many=True, required=False, queryset=Node.objects, label=_('Nodes'))
    labels = AssetLabelSerializer(many=True, required=False, label=_('Labels'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    accounts = AssetAccountSerializer(many=True, required=False, label=_('Account'))

    class Meta:
        model = Asset
        fields_mini = ['id', 'name', 'address']
        fields_small = fields_mini + ['is_active', 'comment']
        fields_fk = ['domain', 'platform', 'platform']
        fields_m2m = [
            'nodes', 'labels', 'protocols', 'accounts', 'nodes_display',
        ]
        read_only_fields = [
            'category', 'type', 'info',
            'connectivity', 'date_verified',
            'created_by', 'date_created'
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        extra_kwargs = {
            'name': {'label': _("Name")},
            'address': {'label': _('Address')},
            'nodes_display': {'label': _('Node path')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('domain', 'platform', 'protocols') \
            .annotate(category=F("platform__category")) \
            .annotate(type=F("platform__type"))
        queryset = queryset.prefetch_related('nodes', 'labels', 'accounts')
        return queryset

    def perform_nodes_display_create(self, instance, nodes_display):
        if not nodes_display:
            return
        nodes_to_set = []
        for full_value in nodes_display:
            if not full_value.startswith('/'):
                full_value = '/' + instance.org.name + '/' + full_value
            node = Node.objects.filter(full_value=full_value).first()
            if node:
                nodes_to_set.append(node)
            else:
                node = Node.create_node_by_full_value(full_value)
            nodes_to_set.append(node)
        instance.nodes.set(nodes_to_set)

    def validate_nodes(self, nodes):
        if nodes:
            return nodes
        request = self.context.get('request')
        if not request:
            return []
        node_id = request.query_params.get('node_id')
        if not node_id:
            return []

    def validate_protocols(self, protocols_data):
        if not protocols_data:
            protocols_data = []
        platform_id = self.initial_data.get('platform')
        if isinstance(platform_id, dict):
            platform_id = platform_id.get('id') or platform_id.get('pk')
        platform = Platform.objects.filter(id=platform_id).first()
        if not platform:
            raise serializers.ValidationError({'platform': _("Platform not exist")})

        protocols_data_map = {p['name']: p for p in protocols_data}
        platform_protocols = platform.protocols.all()
        protocols_default = [p for p in platform_protocols if p.default]
        protocols_required = [p for p in platform_protocols if p.required or p.primary]

        if not protocols_data_map:
            protocols_data_map = {
                p.name: {'name': p.name, 'port': p.port}
                for p in protocols_required + protocols_default
            }

        protocols_not_found = [p.name for p in protocols_required if p.name not in protocols_data_map]
        if protocols_not_found:
            raise serializers.ValidationError({
                'protocols': _("Protocol is required: {}").format(', '.join(protocols_not_found))
            })
        return protocols_data_map.values()

    @atomic
    def create(self, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().create(validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance

    @atomic
    def update(self, instance, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().update(instance, validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance


class AssetDetailSerializer(AssetSerializer):
    accounts = AssetAccountSerializer(many=True, required=False, label=_('Accounts'))
    enabled_info = serializers.SerializerMethodField()

    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + ['accounts', 'enabled_info', 'info', 'specific']

    @staticmethod
    def get_enabled_info(obj):
        platform = obj.platform
        automation = platform.automation
        return {
            'su_enabled': platform.su_enabled,
            'ping_enabled': automation.ping_enabled,
            'domain_enabled': platform.domain_enabled,
            'ansible_enabled': automation.ansible_enabled,
            'protocols_enabled': platform.protocols_enabled,
            'gather_facts_enabled': automation.gather_facts_enabled,
            'change_secret_enabled': automation.change_secret_enabled,
            'verify_account_enabled': automation.verify_account_enabled,
            'gather_accounts_enabled': automation.gather_accounts_enabled,
        }


class MiniAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = AssetSerializer.Meta.fields_mini


class AssetSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = [
            'id', 'name', 'address', 'port',
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
    accounts = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects, required=False, allow_empty=True, many=True
    )
