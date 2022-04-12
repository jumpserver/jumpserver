from django.db import models
from django.utils.translation import gettext_lazy as _

from .common import Asset
from .device_info import DeviceInfo


class Network(Asset):
    device_info = models.ForeignKey(DeviceInfo, on_delete=models.SET_NULL,
                                    null=True, verbose_name=_("Device info"))
