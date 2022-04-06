from django.utils.translation import gettext_lazy as _
from django.db import models

from common.mixins.models import CommonModelMixin
from .common import Asset


class Host(Asset):
    pass


class DeviceInfo(CommonModelMixin):
    host = models.OneToOneField(Host, related_name='device_info', on_delete=models.CASCADE,
                                verbose_name=_("Host"), unique=True)
    # Collect
    vendor = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Vendor'))
    model = models.CharField(max_length=54, null=True, blank=True, verbose_name=_('Model'))
    sn = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Serial number'))

    cpu_model = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('CPU model'))
    cpu_count = models.IntegerField(null=True, verbose_name=_('CPU count'))
    cpu_cores = models.IntegerField(null=True, verbose_name=_('CPU cores'))
    cpu_vcpus = models.IntegerField(null=True, verbose_name=_('CPU vcpus'))
    memory = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Memory'))
    disk_total = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk total'))
    disk_info = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk info'))

    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    os_version = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('OS version'))
    os_arch = models.CharField(max_length=16, blank=True, null=True, verbose_name=_('OS arch'))
    hostname_raw = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Hostname raw'))

    @property
    def cpu_info(self):
        info = ""
        if self.cpu_model:
            info += self.cpu_model
        if self.cpu_count and self.cpu_cores:
            info += "{}*{}".format(self.cpu_count, self.cpu_cores)
        return info

    @property
    def hardware_info(self):
        if self.cpu_count:
            return '{} Core {} {}'.format(
                self.cpu_vcpus or self.cpu_count * self.cpu_cores,
                self.memory, self.disk_total
            )
        else:
            return ''

    def __str__(self):
        return '{} of {}'.format(self.hardware_info, self.host.hostname)

    class Meta:
        verbose_name = _("DeviceInfo")
