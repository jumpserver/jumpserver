from rest_framework import serializers

from .common import AssetSerializer
from assets.models import HostInfo


class HardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = HostInfo
        fields = [
            'id', 'vendor', 'model', 'sn', 'cpu_model', 'cpu_count',
            'cpu_cores', 'cpu_vcpus', 'memory', 'disk_total', 'disk_info',
            'os', 'os_version', 'os_arch', 'hostname_raw',
            'cpu_info', 'hardware_info', 'date_updated'
        ]


class HostSerializer(AssetSerializer):
    hardware_info = HardwareSerializer(read_only=True)
