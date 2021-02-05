# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.db.models import F
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Asset, Node, Platform
from .base import ConnectivitySerializer

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer',
    'AssetDisplaySerializer',
    'ProtocolsField', 'PlatformSerializer',
    'AssetDetailSerializer', 'AssetTaskSerializer',
]


class ProtocolField(serializers.RegexField):
    protocols = '|'.join(dict(Asset.PROTOCOL_CHOICES).keys())
    default_error_messages = {
        'invalid': _('Protocol format should {}/{}'.format(protocols, '1-65535'))
    }
    regex = r'^(%s)/(\d{1,5})$' % protocols

    def __init__(self, *args, **kwargs):
        super().__init__(self.regex, **kwargs)


def validate_duplicate_protocols(values):
    errors = []
    names = []

    for value in values:
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
        kwargs['max_length'] = 4
        super().__init__(*args, **kwargs)

    def to_representation(self, value):
        if not value:
            return []
        return value.split(' ')


class AssetSerializer(BulkOrgResourceModelSerializer):
    platform = serializers.SlugRelatedField(
        slug_field='name', queryset=Platform.objects.all(), label=_("Platform")
    )
    protocols = ProtocolsField(label=_('Protocols'), required=False)
    domain_display = serializers.ReadOnlyField(source='domain.name', label=_('Domain name'))
    admin_user_display = serializers.ReadOnlyField(source='admin_user.name', label=_('Admin user name'))
    nodes_display = serializers.ListField(child=serializers.CharField(), label=_('Nodes name'), required=False)

    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        fields_mini = ['id', 'hostname', 'ip']
        fields_small = fields_mini + [
            'protocol', 'port', 'protocols', 'is_active', 'public_ip',
            'number', 'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw', 'comment',
            'created_by', 'date_created', 'hardware_info',
        ]
        fields_fk = [
            'admin_user', 'admin_user_display', 'domain', 'domain_display', 'platform'
        ]
        fk_only_fields = {
            'platform': ['name']
        }
        fields_m2m = [
            'nodes', 'nodes_display', 'labels',
        ]
        annotates_fields = {
            # 'admin_user_display': 'admin_user__name'
        }
        fields_as = list(annotates_fields.keys())
        fields = fields_small + fields_fk + fields_m2m + fields_as
        read_only_fields = [
            'created_by', 'date_created',
        ] + fields_as

        extra_kwargs = {
            'protocol': {'write_only': True},
            'port': {'write_only': True},
            'hardware_info': {'label': _('Hardware info')},
            'org_name': {'label': _('Org name')}
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('admin_user', 'domain', 'platform')
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
            validated_data["protocols"] = ' '.join(protocols_data)

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

    def create(self, validated_data):
        self.compatible_with_old_protocol(validated_data)
        nodes_display = validated_data.pop('nodes_display', '')
        instance = super().create(validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance

    def update(self, instance, validated_data):
        nodes_display = validated_data.pop('nodes_display', '')
        self.compatible_with_old_protocol(validated_data)
        instance = super().update(instance, validated_data)
        self.perform_nodes_display_create(instance, nodes_display)
        return instance


class AssetDisplaySerializer(AssetSerializer):
    connectivity = ConnectivitySerializer(read_only=True, label=_("Connectivity"))

    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + [
            'connectivity',
        ]


class PlatformSerializer(serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO 修复 drf SlugField RegexValidator bug，之后记得删除
        validators = self.fields['name'].validators
        if isinstance(validators[-1], RegexValidator):
            validators.pop()

    class Meta:
        model = Platform
        fields = [
            'id', 'name', 'base', 'charset',
            'internal', 'meta', 'comment'
        ]


class AssetDetailSerializer(AssetSerializer):
    platform = PlatformSerializer(read_only=True)


class AssetSimpleSerializer(serializers.ModelSerializer):
    connectivity = ConnectivitySerializer(read_only=True, label=_("Connectivity"))

    class Meta:
        model = Asset
        fields = ['id', 'hostname', 'ip', 'connectivity', 'port']


class AssetTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('refresh', 'refresh'),
        ('test', 'test'),
    )
    task = serializers.CharField(read_only=True)
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    assets = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, required=False, allow_empty=True, many=True
    )
