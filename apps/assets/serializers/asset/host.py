from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from assets.models import Host
from .common import AssetSerializer


__all__ = ['HostInfoSerializer', 'HostSerializer']


class HostInfoSerializer(serializers.Serializer):
    vendor = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Vendor'))
    model = serializers.CharField(max_length=54, required=False, allow_blank=True,  label=_('Model'))
    sn = serializers.CharField(max_length=128, required=False, allow_blank=True,  label=_('Serial number'))
    cpu_model = serializers.ListField(child=serializers.CharField(max_length=64, allow_blank=True), required=False, label=_('CPU model'))
    cpu_count = serializers.IntegerField(required=False, label=_('CPU count'))
    cpu_cores = serializers.IntegerField(required=False, label=_('CPU cores'))
    cpu_vcpus = serializers.IntegerField(required=False, label=_('CPU vcpus'))
    memory = serializers.CharField(max_length=64, allow_blank=True, required=False, label=_('Memory'))
    disk_total = serializers.CharField(max_length=1024, allow_blank=True, required=False, label=_('Disk total'))

    distribution = serializers.CharField(max_length=128, allow_blank=True, required=False, label=_('OS'))
    distribution_version = serializers.CharField(max_length=16,  allow_blank=True, required=False, label=_('OS version'))
    arch = serializers.CharField(max_length=16, allow_blank=True, required=False, label=_('OS arch'))


class HostSerializer(AssetSerializer):
    info = HostInfoSerializer(required=False)

    class Meta(AssetSerializer.Meta):
        model = Host
        fields = AssetSerializer.Meta.fields + ['info']
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': _("IP/Host")
            },
        }


