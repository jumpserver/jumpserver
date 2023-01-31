# -*- coding: utf-8 -*-
#

from django.db.models import F
from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from accounts.models import Account, AccountTemplate
from accounts.serializers import AccountSerializerCreateValidateMixin
from common.serializers import WritableNestedModelSerializer, SecretReadableMixin, CommonModelSerializer
from common.serializers.fields import LabeledChoiceField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ...const import Category, AllTypes
from ...models import Asset, Node, Platform, Label, Protocol

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer', 'AssetProtocolsSerializer',
    'AssetDetailSerializer', 'DetailMixin', 'AssetAccountSerializer',
    'AccountSecretSerializer'
]


class AssetProtocolsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Protocol
        fields = ['name', 'port']


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


class AssetAccountSerializer(
    AccountSerializerCreateValidateMixin, CommonModelSerializer
):
    add_org_fields = False
    push_now = serializers.BooleanField(
        default=False, label=_("Push now"), write_only=True
    )

    class Meta:
        model = Account
        fields_mini = [
            'id', 'name', 'username', 'privileged',
            'version', 'secret_type',
        ]
        fields_write_only = [
            'secret', 'push_now'
        ]
        fields = fields_mini + fields_write_only
        extra_kwargs = {
            'secret': {'write_only': True},
        }

    def validate_name(self, value):
        if not value:
            value = self.initial_data.get('username')
        return value

    @staticmethod
    def validate_template(value):
        try:
            return AccountTemplate.objects.get(id=value)
        except AccountTemplate.DoesNotExist:
            raise serializers.ValidationError(_('Account template not found'))

    @staticmethod
    def replace_attrs(account_template: AccountTemplate, attrs: dict):
        exclude_fields = [
            '_state', 'org_id', 'id', 'date_created',
            'date_updated'
        ]
        template_attrs = {
            k: v for k, v in account_template.__dict__.items()
            if k not in exclude_fields
        }
        for k, v in template_attrs.items():
            attrs.setdefault(k, v)

    def create(self, validated_data):
        from accounts.tasks import push_accounts_to_assets
        instance = super().create(validated_data)
        if self.push_now:
            push_accounts_to_assets.delay([instance.id], [instance.asset_id])
        return instance


class AccountSecretSerializer(SecretReadableMixin, CommonModelSerializer):
    class Meta:
        model = Account
        fields = [
            'name', 'username', 'privileged', 'secret_type', 'secret',
        ]
        extra_kwargs = {
            'secret': {'write_only': False},
        }


class AssetSerializer(BulkOrgResourceModelSerializer, WritableNestedModelSerializer):
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))
    labels = AssetLabelSerializer(many=True, required=False, label=_('Label'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'))
    accounts = AssetAccountSerializer(many=True, required=False, write_only=True, label=_('Account'))
    enabled_info = serializers.DictField(read_only=True, label=_('Enabled info'))

    class Meta:
        model = Asset
        fields_mini = ['id', 'name', 'address']
        fields_small = fields_mini + ['is_active', 'comment']
        fields_fk = ['domain', 'platform']
        fields_m2m = [
            'nodes', 'labels', 'protocols', 'nodes_display', 'accounts'
        ]
        read_only_fields = [
            'category', 'type', 'info', 'enabled_info',
            'connectivity', 'date_verified',
            'created_by', 'date_created'
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        extra_kwargs = {
            'name': {'label': _("Name")},
            'address': {'label': _('Address')},
            'nodes_display': {'label': _('Node path')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_field_choices()

    def _init_field_choices(self):
        request = self.context.get('request')
        if not request:
            return
        category = request.path.strip('/').split('/')[-1].rstrip('s')
        field_category = self.fields.get('category')
        field_category._choices = Category.filter_choices(category)
        field_type = self.fields.get('type')
        field_type._choices = AllTypes.filter_choices(category)

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('domain', 'platform') \
            .annotate(category=F("platform__category")) \
            .annotate(type=F("platform__type"))
        queryset = queryset.prefetch_related('nodes', 'labels', 'protocols')
        return queryset

    @staticmethod
    def perform_nodes_display_create(instance, nodes_display):
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


class DetailMixin(serializers.Serializer):
    accounts = AssetAccountSerializer(many=True, required=False, label=_('Accounts'))

    def get_field_names(self, declared_fields, info):
        names = super().get_field_names(declared_fields, info)
        names.extend([
            'accounts', 'info', 'specific', 'spec_info'
        ])
        return names


class AssetDetailSerializer(DetailMixin, AssetSerializer):
    pass


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
