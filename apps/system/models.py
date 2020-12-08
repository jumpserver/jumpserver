import time

from django.db import models
import psutil
from django.utils import timezone

from django.utils.translation import ugettext_lazy as _


class Stat(models.Model):
    class Components(models.TextChoices):
        core = 'core', 'Core'
        koko = 'koko', 'KoKo'
        guacamole = 'guacamole', 'Guacamole'
        omnidb = 'omnidb', 'OmniDB'

    class Keys(models.TextChoices):
        cpu_load_1 = 'cpu_load', 'CPU load'
        memory_used_percent = 'memory_used_percent', _('Memory used percent')
        disk_used_percent = 'disk_used_percent', _('Disk used percent')
        session_active = 'session_active', _('Session active')
        session_processed = 'session_processed', _('Session processed')

    node = models.CharField(max_length=128)
    ip = models.GenericIPAddressField()
    component = models.CharField(choices=Components.choices, max_length=16)
    key = models.CharField(db_index=True, max_length=16, verbose_name=_('Item key'))
    value = models.FloatField()
    datetime = models.DateTimeField()

    def __str__(self):
        return f'{self.key}:{self.value}'

    @staticmethod
    def collect_local_stats():
        memory_percent = psutil.virtual_memory().percent
        cpu_load = psutil.getloadavg()
        cpu_load_1 = round(cpu_load[0], 2)
        cpu_load_5 = round(cpu_load[1], 2)
        cpu_load_15 = round(cpu_load[2], 2)
        cpu_percent = psutil.cpu_percent()
        stats = dict(
            memory_percent=memory_percent,
            cpu_load_1=cpu_load_1,
            cpu_load_5=cpu_load_5,
            cpu_load_15=cpu_load_15,
            cpu_load=cpu_load_1,
            cpu_percent=cpu_percent
        )
        return stats

    @classmethod
    def keep_collect_local_stats(cls):
        data = {
            'node': 'core-01',
            'ip': '192.168.1.1',
            'component': 'core'
        }
        while True:
            stats = cls.collect_local_stats()
            data['datetime'] = timezone.now()
            items = []
            for k, v in stats.items():
                data['key'] = k
                data['value'] = v
                items.append(cls(**data))
            cls.objects.bulk_create(items, ignore_conflicts=True)
            time.sleep(60)
