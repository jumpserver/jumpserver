# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from ...models import Asset, Node, Platform, SystemUser
from ..mixin import CategoryDisplayMixin
from ..account import AccountSerializer

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer', 'MiniAssetSerializer',
    'AssetTaskSerializer', 'AssetsTaskSerializer', 'ProtocolsField',
]


class ProtocolField(serializers.RegexField):
    default_error_messages = {
        'invalid': _('Protocol format should {}/{}').format('protocol', '1-65535')
    }
    regex = r'^(\w+)/(\d{1,5})$'

    def __init__(self, *args, **kwargs):
        super().__init__(self.regex, **kwargs)


def validate_duplicate_protocols(values):
    errors = []
    names = []

    print("Value is: ", values)

    for value in values.split(' '):
        if not value or '/' not in value:
            continue
        name = value.split('/')[0]
        if name in names:
            errors.append(_("Protocol duplicate: {}").format(name))
        names.append(name)
        errors.append('')
    if any(errors):
        raise serializers.ValidationError(errors)


class ProtocolsField(serializers.ListField):
    default_validators = [validate_duplicate_protocols]

    def __init__(self, *args, **kwargs):
        kwargs['child'] = ProtocolField()
        kwargs['allow_null'] = True
        kwargs['allow_empty'] = True
        kwargs['min_length'] = 1
        kwargs['max_length'] = 32
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if not value:
            return []
        if isinstance(value, str):
            return value.split(' ')
        return value

    def to_internal_value(self, data):
        return ' '.join(data)


class AssetSerializer(CategoryDisplayMixin, OrgResourceModelSerializerMixin):
    protocols = ProtocolsField(label=_('Protocols'), required=False, default=['ssh/22'])
    domain_display = serializers.ReadOnlyField(source='domain.name', label=_('Domain name'))
    nodes_display = serializers.ListField(
        child=serializers.CharField(), label=_('Nodes name'), required=False
    )
    labels_display = serializers.ListField(
        child=serializers.CharField(), label=_('Labels name'),
        required=False, read_only=True
    )
    platform_display = serializers.SlugField(
        source='platform.name', label=_("Platform display"), read_only=True
    )
    accounts = AccountSerializer(many=True, write_only=True, required=False)

    """
    资产的数据结构
    """

    class Meta:
        model = Asset
        fields_mini = [
            'id', 'hostname', 'ip', 'platform', 'protocols'
        ]
        fields_small = fields_mini + [
            'protocol', 'port', 'is_active',
            'public_ip', 'number', 'comment',
        ]
        fields_fk = [
            'domain', 'domain_display', 'platform',
        ]
        fields_m2m = [
            'nodes', 'nodes_display', 'labels', 'labels_display', 'accounts'
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
        queryset = queryset.prefetch_related('domain', 'platform')
        queryset = queryset.prefetch_related('nodes', 'labels')
        return queryset

    def compatible_with_old_protocol(self, validated_data):
        protocols_data = validated_data.pop("protocols", [])

        # 兼容老的api
        name = validated_data.get("protocol")
        port = validated_data.get("port")
        if not protocols_data and name and port:
            protocols_data.insert(0, '/'.join([name, str(port)]))
        elif not name and not port and protocols_data:
            protocol = protocols_data[0].split('/')
            validated_data["protocol"] = protocol[0]
            validated_data["port"] = int(protocol[1])
        if protocols_data:
            validated_data["protocols"] = protocols_data

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
