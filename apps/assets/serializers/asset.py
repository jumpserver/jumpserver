# -*- coding: utf-8 -*-
#
import re
from rest_framework import serializers
from django.db.models import Prefetch
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.serializers import AdaptedBulkListSerializer
from ..models import Asset, Node, Label, Platform
from ..const import (
    GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_PATTERN,
    GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_ERROR_MSG
)
from .base import ConnectivitySerializer

__all__ = [
    'AssetSerializer', 'AssetSimpleSerializer',
    'ProtocolsField', 'PlatformSerializer',
    'AssetDetailSerializer',
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
    connectivity = ConnectivitySerializer(read_only=True, label=_("Connectivity"))

    """
    资产的数据结构
    """
    class Meta:
        model = Asset
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'ip', 'hostname', 'protocol', 'port',
            'protocols', 'platform', 'is_active', 'public_ip', 'domain',
            'admin_user', 'nodes', 'labels', 'number', 'vendor', 'model', 'sn',
            'cpu_model', 'cpu_count', 'cpu_cores', 'cpu_vcpus', 'memory',
            'disk_total', 'disk_info', 'os', 'os_version', 'os_arch',
            'hostname_raw', 'comment', 'created_by', 'date_created',
            'hardware_info', 'connectivity',
        ]
        read_only_fields = (
            'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw',
            'created_by', 'date_created',
        )
        extra_kwargs = {
            'protocol': {'write_only': True},
            'port': {'write_only': True},
            'hardware_info': {'label': _('Hardware info')},
            'org_name': {'label': _('Org name')}
        }

    @staticmethod
    def validate_hostname(hostname):
        pattern = GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_PATTERN
        res = re.search(pattern, hostname)
        if res is not None:
            msg = GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_ERROR_MSG
            raise serializers.ValidationError(msg)
        return hostname

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            Prefetch('nodes', queryset=Node.objects.all().only('id')),
            Prefetch('labels', queryset=Label.objects.all().only('id')),
        ).select_related('admin_user', 'domain', 'platform')
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
