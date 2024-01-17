# -*- coding: utf-8 -*-
#

from django.db.models import F
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import Account
from accounts.serializers import AccountSerializer
from common.const import UUID_PATTERN
from common.serializers import (
    WritableNestedModelSerializer, SecretReadableMixin,
    CommonModelSerializer, MethodSerializer, ResourceLabelsMixin
)
from common.serializers.common import DictSerializer
from common.serializers.fields import LabeledChoiceField
from labels.models import Label
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ...const import Category, AllTypes
from ...models import Asset, Node, Platform, Protocol

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer', 'AssetProtocolsSerializer',
    'AssetDetailSerializer', 'DetailMixin', 'AssetAccountSerializer',
    'AccountSecretSerializer', 'AssetProtocolsPermsSerializer', 'AssetLabelSerializer'
]


class AssetProtocolsSerializer(serializers.ModelSerializer):
    port = serializers.IntegerField(required=False, allow_null=True, max_value=65535, min_value=0)

    def to_file_representation(self, data):
        return '{name}/{port}'.format(**data)

    def to_file_internal_value(self, data):
        name, port = data.split('/')
        return {'name': name, 'port': port}

    class Meta:
        model = Protocol
        fields = ['name', 'port']


class AssetProtocolsPermsSerializer(AssetProtocolsSerializer):
    class Meta(AssetProtocolsSerializer.Meta):
        fields = AssetProtocolsSerializer.Meta.fields + ['public', 'setting']


class AssetLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Label
        fields = ['id', 'name', 'value']
        extra_kwargs = {
            # 取消默认唯一键的校验
            'id': {'validators': []},
            'name': {'required': False},
            'value': {'required': False},
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
    asset = serializers.PrimaryKeyRelatedField(queryset=Asset.objects, required=False, write_only=True)
    clone_id = None

    def to_internal_value(self, data):
        # 导入时，data有时为str
        if isinstance(data, str):
            return super().to_internal_value(data)

        clone_id = data.pop('id', None)
        ret = super().to_internal_value(data)
        self.clone_id = clone_id
        return ret

    def set_secret(self, attrs):
        _id = self.clone_id
        if not _id:
            return attrs

        account = Account.objects.get(id=_id)
        attrs['secret'] = account.secret
        return attrs

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self.set_secret(attrs)

    class Meta(AccountSerializer.Meta):
        fields = [
            f for f in AccountSerializer.Meta.fields
            if f not in [
                'spec_info', 'connectivity', 'labels', 'created_by',
                'date_update', 'date_created'
            ]
        ]
        extra_kwargs = {
            **AccountSerializer.Meta.extra_kwargs,
        }


class AccountSecretSerializer(SecretReadableMixin, CommonModelSerializer):
    class Meta:
        model = Account
        fields = [
            'name', 'username', 'privileged', 'secret_type', 'secret',
        ]
        extra_kwargs = {
            'secret': {'write_only': False},
        }


class AssetSerializer(BulkOrgResourceModelSerializer, ResourceLabelsMixin, WritableNestedModelSerializer):
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))
    protocols = AssetProtocolsSerializer(many=True, required=False, label=_('Protocols'), default=())
    accounts = AssetAccountSerializer(many=True, required=False, allow_null=True, write_only=True, label=_('Account'))
    nodes_display = serializers.ListField(read_only=False, required=False, label=_("Node path"))
    _accounts = None

    class Meta:
        model = Asset
        fields_mini = ['id', 'name', 'address']
        fields_small = fields_mini + ['is_active', 'comment']
        fields_fk = ['domain', 'platform']
        fields_m2m = [
            'nodes', 'labels', 'protocols',
            'nodes_display', 'accounts',
        ]
        read_only_fields = [
            'category', 'type', 'connectivity', 'auto_config',
            'date_verified', 'created_by', 'date_created',
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        fields_unexport = ['auto_config']
        extra_kwargs = {
            'auto_config': {'label': _('Auto info')},
            'name': {'label': _("Name")},
            'address': {'label': _('Address')},
            'nodes_display': {'label': _('Node path')},
            'nodes': {'allow_empty': True},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_field_choices()
        self._extract_accounts()

    def _extract_accounts(self):
        if not getattr(self, 'initial_data', None):
            return
        if isinstance(self.initial_data, list):
            return
        accounts = self.initial_data.pop('accounts', None)
        self._accounts = accounts

    def _get_protocols_required_default(self):
        platform = self._asset_platform
        platform_protocols = platform.protocols.all()
        protocols_default = [p for p in platform_protocols if p.default]
        protocols_required = [p for p in platform_protocols if p.required or p.primary]
        return protocols_required, protocols_default

    def _set_protocols_default(self):
        if not hasattr(self, 'initial_data'):
            return
        protocols = self.initial_data.get('protocols')
        if protocols is not None:
            return
        if getattr(self, 'instance', None):
            return

        protocols_required, protocols_default = self._get_protocols_required_default()
        protocol_map = {str(protocol.id): protocol for protocol in protocols_required + protocols_default}
        protocols = list(protocol_map.values())
        protocols_data = [{'name': p.name, 'port': p.port} for p in protocols]
        self.initial_data['protocols'] = protocols_data

    def _init_field_choices(self):
        request = self.context.get('request')
        if not request:
            return
        category = request.path.strip('/').split('/')[-1].rstrip('s')
        field_category = self.fields.get('category')
        if not field_category:
            return
        field_category.choices = Category.filter_choices(category)
        field_type = self.fields.get('type')
        if not field_type:
            return
        field_type.choices = AllTypes.filter_choices(category)

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('domain', 'nodes', 'protocols', ) \
            .prefetch_related('platform', 'platform__automation') \
            .annotate(category=F("platform__category")) \
            .annotate(type=F("platform__type"))
        if queryset.model is Asset:
            queryset = queryset.prefetch_related('labels__label', 'labels')
        else:
            queryset = queryset.prefetch_related('asset_ptr__labels__label', 'asset_ptr__labels')
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

    @property
    def _asset_platform(self):
        platform_id = self.initial_data.get('platform')
        if isinstance(platform_id, dict):
            platform_id = platform_id.get('id') or platform_id.get('pk')

        if not platform_id and self.instance:
            platform = self.instance.platform
        else:
            platform = Platform.objects.filter(id=platform_id).first()

        if not platform:
            raise serializers.ValidationError({'platform': _("Platform not exist")})
        return platform

    def validate_domain(self, value):
        platform = self._asset_platform
        if platform.domain_enabled:
            return value
        else:
            return None

    def validate_nodes(self, nodes):
        if nodes:
            return nodes
        nodes_display = self.initial_data.get('nodes_display')
        if nodes_display:
            return nodes
        default_node = Node.org_root()
        request = self.context.get('request')
        if not request:
            return [default_node]
        node_id = request.query_params.get('node_id')
        if not node_id:
            return [default_node]
        nodes = Node.objects.filter(id=node_id)
        return nodes

    def is_valid(self, raise_exception=False):
        self._set_protocols_default()
        return super().is_valid(raise_exception=raise_exception)

    def validate_protocols(self, protocols_data):
        # 目的是去重
        protocols_data_map = {p['name']: p for p in protocols_data}
        for p in protocols_data:
            port = p.get('port', 0)
            if port < 0 or port > 65535:
                error = p.get('name') + ': ' + _("port out of range (0-65535)")
                raise serializers.ValidationError(error)

        protocols_required, __ = self._get_protocols_required_default()
        protocols_not_found = [p.name for p in protocols_required if p.name not in protocols_data_map]
        if protocols_not_found:
            raise serializers.ValidationError({
                'protocols': _("Protocol is required: {}").format(', '.join(protocols_not_found))
            })
        return protocols_data_map.values()

    @staticmethod
    def update_account_su_from(accounts, include_su_from_accounts):
        if not include_su_from_accounts:
            return
        name_map = {account.name: account for account in accounts}
        username_secret_type_map = {
            (account.username, account.secret_type): account for account in accounts
        }

        for name, username_secret_type in include_su_from_accounts.items():
            account = name_map.get(name)
            if not account:
                continue
            su_from_account = username_secret_type_map.get(username_secret_type)
            if su_from_account:
                account.su_from = su_from_account
                account.save()

    def accounts_create(self, accounts_data, asset):
        from accounts.models import AccountTemplate
        if not accounts_data:
            return

        if not isinstance(accounts_data[0], dict):
            raise serializers.ValidationError({'accounts': _("Invalid data")})

        su_from_name_username_secret_type_map = {}
        for data in accounts_data:
            data['asset'] = asset.id
            name = data.get('name')
            su_from = data.pop('su_from', None)
            template_id = data.get('template', None)
            if template_id:
                template = AccountTemplate.objects.get(id=template_id)
                if template and template.su_from:
                    su_from_name_username_secret_type_map[template.name] = (
                        template.su_from.username, template.su_from.secret_type
                    )
            elif isinstance(su_from, dict):
                su_from = Account.objects.get(id=su_from.get('id'))
                su_from_name_username_secret_type_map[name] = (
                    su_from.username, su_from.secret_type
                )
        s = AssetAccountSerializer(data=accounts_data, many=True)
        s.is_valid(raise_exception=True)
        accounts = s.save()
        self.update_account_su_from(accounts, su_from_name_username_secret_type_map)

    @atomic
    def create(self, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().create(validated_data)
        self.accounts_create(self._accounts, instance)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance

    @staticmethod
    def sync_platform_protocols(instance, old_platform):
        platform = instance.platform

        if str(old_platform.id) == str(instance.platform_id):
            return

        platform_protocols = {
            p['name']: p['port']
            for p in platform.protocols.values('name', 'port')
        }

        protocols = set(instance.protocols.values_list('name', flat=True))
        protocol_names = set(platform_protocols) - protocols
        objs = []
        for name in protocol_names:
            objs.append(
                Protocol(
                    name=name,
                    port=platform_protocols[name],
                    asset_id=instance.id,
                )
            )
        Protocol.objects.bulk_create(objs)

    @atomic
    def update(self, instance, validated_data):
        old_platform = instance.platform
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().update(instance, validated_data)
        self.sync_platform_protocols(instance, old_platform)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance


class DetailMixin(serializers.Serializer):
    spec_info = MethodSerializer(label=_('Spec info'), read_only=True)
    gathered_info = MethodSerializer(label=_('Gathered info'), read_only=True)
    auto_config = serializers.DictField(read_only=True, label=_('Auto info'))

    def get_instance(self):
        request = self.context.get('request')
        if not self.instance and UUID_PATTERN.findall(request.path):
            pk = UUID_PATTERN.findall(request.path)[0]
            self.instance = Asset.objects.filter(id=pk).first()
        return self.instance

    def get_field_names(self, declared_fields, info):
        names = super().get_field_names(declared_fields, info)
        names.extend([
            'gathered_info', 'spec_info', 'auto_config',
        ])
        return names

    def get_category(self):
        request = self.context.get('request')
        if request.query_params.get('category'):
            category = request.query_params.get('category')
        else:
            instance = self.get_instance()
            category = instance.category if instance else 'host'
        return category

    def get_gathered_info_serializer(self):
        category = self.get_category()
        from .info.gathered import category_gathered_serializer_map
        serializer_cls = category_gathered_serializer_map.get(category, DictSerializer)
        return serializer_cls()

    def get_spec_info_serializer(self):
        category = self.get_category()
        from .info.spec import category_spec_serializer_map
        serializer_cls = category_spec_serializer_map.get(category, DictSerializer)
        return serializer_cls()


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
