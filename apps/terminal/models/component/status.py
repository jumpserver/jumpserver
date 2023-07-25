import uuid

from django.core.cache import cache
from django.db import models
from django.forms.models import model_to_dict
from django.utils.translation import gettext_lazy as _

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
        verbose_name = _("Status")

    @classmethod
    def get_terminal_latest_stat(cls, terminal):
        key = cls.CACHE_KEY.format(terminal.id)
        data = cache.get(key)
        if not data:
            return None
        data.pop('terminal', None)
        stat = cls(**data)
        stat.terminal = terminal
        stat.is_alive = terminal.is_alive
        stat.keep_one_decimal_place()
        return stat

    def keep_one_decimal_place(self):
        keys = ['cpu_load', 'memory_used', 'disk_used']
        for key in keys:
            value = getattr(self, key, 0)
            if not isinstance(value, (int, float)):
                continue
            value = '%.1f' % value
            setattr(self, key, float(value))

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.terminal.set_alive(ttl=60 * 3)
        return self.save_to_cache()

    def save_to_cache(self):
        if not self.terminal:
            return
        key = self.CACHE_KEY.format(self.terminal.id)
        data = model_to_dict(self)
        cache.set(key, data, 60 * 3)
        return data
