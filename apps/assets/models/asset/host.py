# from django.db import models
# from django.utils.translation import gettext_lazy as _

from assets.const import Category
from .common import Asset
# from .device_info import DeviceInfo


class Host(Asset):
    def save(self, *args, **kwargs):
        self.category = Category.HOST
        return super().save(*args, **kwargs)


