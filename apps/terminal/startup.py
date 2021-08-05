import os
import time
import socket
import threading
from django.conf import settings
from common.decorator import Singleton
from common.utils import get_disk_usage, get_cpu_load, get_memory_usage, get_logger
from .serializers.terminal import TerminalRegistrationSerializer, StatusSerializer
from .const import TerminalTypeChoices
from .models.terminal import Terminal

__all__ = ['CoreTerminal', 'CeleryTerminal']


class BaseTerminal(object):

    def __init__(self, suffix_name, _type):
        self.server_hostname = os.environ.get('SERVER_HOSTNAME') or socket.gethostname()
        self.name = f'[{suffix_name}] {self.server_hostname}'
        self.interval = 30
        self.remote_addr = socket.gethostbyname(socket.gethostname())
        self.type = _type

    def start_heartbeat_thread(self):
        print(f'-- Start {self.name} heartbeat thread')
        t = threading.Thread(target=self.start_heartbeat)
        t.setDaemon(True)
        t.start()

    def start_heartbeat(self):
        while True:
            heartbeat_data = {
                'cpu_load': get_cpu_load(),
                'memory_used': get_memory_usage(),
                'disk_used': get_disk_usage(path=settings.BASE_DIR),
                'sessions': [],
            }
            status_serializer = StatusSerializer(data=heartbeat_data)
            status_serializer.is_valid()
            status_serializer.validated_data.pop('sessions', None)
            terminal = self.get_or_register_terminal()
            status_serializer.validated_data['terminal'] = terminal
            status_serializer.save()

            time.sleep(self.interval)

    def get_or_register_terminal(self):
        terminal = Terminal.objects.filter(name=self.name, type=self.type).first()
        if not terminal:
            terminal = self.register_terminal()
        return terminal

    def register_terminal(self):
        data = {'name': self.name, 'type': self.type, 'remote_addr': self.remote_addr}
        serializer = TerminalRegistrationSerializer(data=data)
        serializer.is_valid()
        terminal = serializer.save()
        return terminal


@Singleton
class CoreTerminal(BaseTerminal):

    def __init__(self):
        super().__init__(
            suffix_name=TerminalTypeChoices.core.label, _type=TerminalTypeChoices.core.value
        )


@Singleton
class CeleryTerminal(BaseTerminal):
    def __init__(self):
        super().__init__(
            suffix_name=TerminalTypeChoices.celery.label, _type=TerminalTypeChoices.celery.value
        )
