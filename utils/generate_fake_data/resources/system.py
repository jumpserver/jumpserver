import random

from .base import FakeDataGenerator
from terminal.models import *


class StatGenerator(FakeDataGenerator):
    resource = 'stat'

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
    items_value_range = {
        'cpu_load': (0, 3.0),
        'memory_used_percent': (20, 10.0),
        'disk_used_percent': (30, 80.0),
        'thread': (100, 100),
        'goroutine': (200, 500),
        'replay_upload_health': (0, [0, 1]),
        'command_upload_health': (0, [0, 1]),
        'session_active': (100, 50),
        'session_processed': (400, 400),
        'session_failed': (50, 100),
        'session_succeeded': (500, 300)
    }

    def do_generate(self, batch, batch_size):
        datetime = timezone.now()
        for i in batch:
            datetime = datetime - timezone.timedelta(minutes=1)
            items = []
            for node in self.nodes:
                for key, values in self.items_value_range.items():
                    base, r = values
                    if isinstance(r, int):
                        value = int(random.random() * r)
                    elif isinstance(r, float):
                        value = round(random.random() * r, 2)
                    elif isinstance(r, list):
                        value = random.choice(r)
                    else:
                        continue
                    value += base
                    node.update({
                        'key': key,
                        'value': value,
                        'datetime': datetime
                    })
                    items.append(Stat(**node))
            Stat.objects.bulk_create(items, ignore_conflicts=True)
