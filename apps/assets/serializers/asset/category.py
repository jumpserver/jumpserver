from rest_framework import serializers

from assets.models import DeviceInfo, Host, Database, Network, Cloud
from .common import AssetSerializer

__all__ = [
    'DeviceSerializer', 'HostSerializer', 'DatabaseSerializer',
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
        fields = AssetSerializer.Meta.fields + ['db_name']


class NetworkSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Network


class CloudSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Cloud
