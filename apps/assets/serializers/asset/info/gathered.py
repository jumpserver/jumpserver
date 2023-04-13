from django.utils.translation import gettext_lazy as _
from rest_framework import serializers


class HostGatheredInfoSerializer(serializers.Serializer):
    vendor = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Vendor'))
    model = serializers.CharField(max_length=54, required=False, allow_blank=True, label=_('Model'))
    sn = serializers.CharField(max_length=128, required=False, allow_blank=True, label=_('Serial number'))
    cpu_model = serializers.CharField(max_length=64, allow_blank=True, required=False, label=_('CPU model'))
    cpu_count = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('CPU count'))
    cpu_cores = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('CPU cores'))
    cpu_vcpus = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('CPU vcpus'))
    memory = serializers.CharField(max_length=64, allow_blank=True, required=False, label=_('Memory'))
    disk_total = serializers.CharField(max_length=1024, allow_blank=True, required=False, label=_('Disk total'))

    distribution = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('OS'))
    distribution_version = serializers.CharField(max_length=16, allow_blank=True, required=False, label=_('OS version'))
    arch = serializers.CharField(max_length=16, allow_blank=True, required=False, label=_('OS arch'))


category_gathered_serializer_map = {
    'host': HostGatheredInfoSerializer,
}
