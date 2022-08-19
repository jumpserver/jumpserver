from rest_framework import serializers

from .common import AssetSerializer
from assets.models import DeviceInfo, Host, Database

__all__ = [
    'DeviceSerializer', 'HostSerializer', 'DatabaseSerializer'
]


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceInfo
        fields = [
            'id', 'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw', 'number',
            'cpu_info', 'hardware_info', 'date_updated'
        ]


class HostSerializer(AssetSerializer):
    device_info = DeviceSerializer(read_only=True, allow_null=True)

    class Meta(AssetSerializer.Meta):
        model = Host
        fields = AssetSerializer.Meta.fields + ['device_info']


class DatabaseSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Database
        fields_mini = [
            'id', 'name', 'ip', 'db_name',
        ]
        fields_small = fields_mini + [
            'is_active', 'comment',
        ]
        fields_fk = [
            'domain', 'domain_display', 'platform',
        ]
        fields_m2m = [
            'nodes', 'nodes_display', 'labels', 'labels_display',
        ]
        read_only_fields = [
            'category', 'category_display', 'type', 'type_display',
            'created_by', 'date_created',
        ]
        fields = fields_small + fields_fk + fields_m2m + read_only_fields
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'db_name': {'required': True}
        }
