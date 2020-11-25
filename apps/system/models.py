from django.db import models

from django.utils.translation import ugettext_lazy as _
from django.utils import timezone


class Stat(models.Model):
    class Components(models.TextChoices):
        core = 'core', 'Core'
        koko = 'koko', 'KoKo'
        guacamole = 'guacamole', 'Guacamole'
        omnidb = 'omnidb', 'OmniDB'

    class Keys(models.TextChoices):
        cpu = 'cpu', 'CPU'
        memory = 'memory', _('Memory')
        disk = 'disk', _('Disk')
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

    @classmethod
    def generate_fake(cls):
        nodes = [
            {
                'node': 'guacamole-01',
                'ip': '192.168.1.1',
                'component': 'guacamole'
            },
            {
                'node': 'koko-01',
                'ip': '192.168.1.2',
                'component': 'koko'
            },
            {
                'node': 'omnidb-01',
                'ip': '192.168.1.3',
                'component': 'omnidb'
            },
            {
                'node': 'core-01',
                'ip': '192.168.1.4',
                'component': 'core'
            }
        ]
        items_system_type = ['cpu', 'memory', 'disk']
        items_process_type = ['thread', 'goroutine', 'replay_upload_health', 'command_upload_health']
        items_session_type = ['session_active', 'session_processed', 'session_failed', 'session_succeeded']
        items = [
            {
                'node': 'guacamole-01',
                'ip': '192.168.1.1',
                'key': 'cpu',
                'value': 1.1,
                'datetime': timezone
            }
        ]
