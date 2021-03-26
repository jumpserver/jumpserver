from __future__ import unicode_literals

import uuid

from django.db import models
from django.forms.models import model_to_dict
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger


logger = get_logger(__name__)


class Status(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    session_online = models.IntegerField(verbose_name=_("Session Online"), default=0)
    cpu_load = models.FloatField(verbose_name=_("CPU Load"), default=0)
    memory_used = models.FloatField(verbose_name=_("Memory Used"))
    disk_used = models.FloatField(verbose_name=_("Disk Used"), default=0)
    connections = models.IntegerField(verbose_name=_("Connections"), default=0)
    threads = models.IntegerField(verbose_name=_("Threads"), default=0)
    boot_time = models.FloatField(verbose_name=_("Boot Time"), default=0)
    terminal = models.ForeignKey('terminal.Terminal', null=True, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    CACHE_KEY = 'TERMINAL_STATUS_{}'

    class Meta:
        db_table = 'terminal_status'
        get_latest_by = 'date_created'

    def save_to_cache(self):
        if not self.terminal:
            return
        key = self.CACHE_KEY.format(self.terminal.id)
        data = model_to_dict(self)
        cache.set(key, data, 60*3)
        return data

    @classmethod
    def get_terminal_latest_status(cls, terminal):
        from ..utils import ComputeStatUtil
        stat = cls.get_terminal_latest_stat(terminal)
        return ComputeStatUtil.compute_component_status(stat)

    @classmethod
    def get_terminal_latest_stat(cls, terminal):
        key = cls.CACHE_KEY.format(terminal.id)
        data = cache.get(key)
        if not data:
            return None
        data.pop('terminal', None)
        stat = cls(**data)
        stat.terminal = terminal
        return stat

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.terminal.set_alive(ttl=120)
        return self.save_to_cache()
        # return super().save()

