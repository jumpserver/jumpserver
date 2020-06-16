# -*- coding: utf-8 -*-
#
from rest_framework import serializers
from django.db.models import Prefetch, F, Count

from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer
from ..models import Asset, Node, Label, Platform
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
    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        list_serializer_class = AdaptedBulkListSerializer
        fields_mini = ['id', 'hostname', 'ip']
        fields_small = fields_mini + [
            'protocol', 'port', 'protocols', 'is_active', 'public_ip',
            'number', 'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw', 'comment',
            'created_by', 'date_created', 'hardware_info',
        ]
        fields_fk = [
            'admin_user', 'admin_user_display', 'domain', 'platform'
        ]
        fk_only_fields = {
            'platform': ['name']
        }
        fields_m2m = [
            'nodes', 'labels',
        ]
        annotates_fields = {
            # 'admin_user_display': 'admin_user__name'
        }
        fields_as = list(annotates_fields.keys())
        fields = fields_small + fields_fk + fields_m2m + fields_as
        read_only_fields = [
            'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw',
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
        queryset = queryset.select_related('admin_user', 'domain', 'platform')
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

    def create(self, validated_data):
        self.compatible_with_old_protocol(validated_data)
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        self.compatible_with_old_protocol(validated_data)
        return super().update(instance, validated_data)


class AssetDisplaySerializer(AssetSerializer):
    connectivity = ConnectivitySerializer(read_only=True, label=_("Connectivity"))

    class Meta(AssetSerializer.Meta):
        fields = AssetSerializer.Meta.fields + [
            'connectivity',
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset\
            .annotate(admin_user_username=F('admin_user__username'))
        return queryset


class PlatformSerializer(serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True)

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
