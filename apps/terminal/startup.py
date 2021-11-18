import os
import time
import socket
import threading
from django.conf import settings
from django.db.utils import OperationalError

from common.db.utils import close_old_connections
from common.decorator import Singleton
from common.utils import get_disk_usage, get_cpu_load, get_memory_usage, get_logger

from .serializers.terminal import TerminalRegistrationSerializer, StatusSerializer
from .const import TerminalTypeChoices
from .models.terminal import Terminal

__all__ = ['CoreTerminal', 'CeleryTerminal']


class BaseTerminal(object):

    def __init__(self, suffix_name, _type):
        server_hostname = os.environ.get('SERVER_HOSTNAME') or ''
        hostname = socket.gethostname()
        if server_hostname:
            name = f'[{suffix_name}]-{server_hostname}'
        else:
            name = f'[{suffix_name}]-{hostname}'
        self.name = name
        self.interval = 30
        self.remote_addr = self.get_remote_addr(hostname)
        self.type = _type

    @staticmethod
    def get_remote_addr(hostname):
        try:
            return socket.gethostbyname(hostname)
        except socket.gaierror:
            return '127.0.0.1'

    def start_heartbeat_thread(self):
        print(f'- Start heartbeat thread => ({self.name})')
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

            try:
                status_serializer.save()
                time.sleep(self.interval)
            except OperationalError:
                close_old_connections()

    def get_or_register_terminal(self):
        terminal = Terminal.objects.filter(
            name=self.name, type=self.type, is_deleted=False
        ).first()
        if not terminal:
            terminal = self.register_terminal()

        terminal.remote_addr = self.remote_addr
        terminal.save()
        return terminal

    def register_terminal(self):
        data = {
            'name': self.name, 'type': self.type,
            'remote_addr': self.remote_addr
        }
        serializer = TerminalRegistrationSerializer(data=data)
        serializer.is_valid()
        terminal = serializer.save()
        return terminal


@Singleton
class CoreTerminal(BaseTerminal):

    def __init__(self):
        super().__init__(
            suffix_name=TerminalTypeChoices.core.label,
            _type=TerminalTypeChoices.core.value
        )


@Singleton
class CeleryTerminal(BaseTerminal):
    def __init__(self):
        super().__init__(
            suffix_name=TerminalTypeChoices.celery.label,
            _type=TerminalTypeChoices.celery.value
        )
