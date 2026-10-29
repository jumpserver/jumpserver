import fcntl
import hashlib
import logging
import os
import socket
import threading
import time

from django.conf import settings
from django.db import connections

from common.db.utils import close_old_connections
from common.decorators import Singleton
from common.utils import get_disk_usage, get_cpu_load, get_memory_usage
from .const import TerminalType
from .models import Terminal
from .serializers.terminal import TerminalRegistrationSerializer, StatSerializer

__all__ = ['CoreTerminal', 'CeleryTerminal']


logger = logging.getLogger(__name__)
_runtime_heartbeats = {}
_runtime_lock = threading.Lock()
_runtime_fork_hooks_registered = False


def _before_fork():
    _runtime_lock.acquire()


def _after_fork_parent():
    _runtime_lock.release()


def _after_fork_child():
    global _runtime_lock
    # Closing an inherited descriptor must not explicitly unlock its shared
    # open-file description: that would also release the parent's flock.
    for heartbeat in _runtime_heartbeats.values():
        if heartbeat.lock_fd is not None:
            os.close(heartbeat.lock_fd)
    _runtime_heartbeats.clear()
    _runtime_lock = threading.Lock()


class RuntimeHeartbeat:
    """One reporter per component identity, with standby threads in other workers."""

    def __init__(self, terminal):
        self.terminal = terminal
        self.pid = os.getpid()
        self.lock_fd = None
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is not None and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self.run, name=f'{self.terminal.type}-heartbeat', daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread is not None and self.thread is not threading.current_thread():
            # A slow database call must not hold up worker shutdown. Keep its
            # lock until the thread really exits (or the process is killed).
            self.thread.join(timeout=1)

    def acquire(self):
        with _runtime_lock:
            if self.lock_fd is None:
                directory = os.path.join(settings.PROJECT_DIR, 'tmp')
                os.makedirs(directory, exist_ok=True)
                identity = f'{self.terminal.type}:{self.terminal.name}'.encode()
                digest = hashlib.sha256(identity).hexdigest()
                path = os.path.join(directory, f'terminal-heartbeat-{digest}.lock')
                self.lock_fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
                os.set_inheritable(self.lock_fd, False)
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return False
        return True

    def close(self):
        with _runtime_lock:
            if self.lock_fd is not None:
                os.close(self.lock_fd)
                self.lock_fd = None
        # Leave the lock file in place; unlinking it can create two lock inodes.

    def run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    if not self.acquire():
                        self.stop_event.wait(min(self.terminal.interval, 5))
                        continue
                    try:
                        close_old_connections()
                        self.terminal.send_runtime_heartbeat()
                    finally:
                        # Django connections are thread-local; only this
                        # heartbeat thread's ORM connections are closed here.
                        connections.close_all()
                except Exception:
                    logger.exception('Component heartbeat failed: %s', self.terminal.name)
                    self.stop_event.wait(self.terminal.interval)
                else:
                    # The legacy loop sleeps twice after a successful report.
                    self.stop_event.wait(self.terminal.interval * 2)
        finally:
            self.close()


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

    def start_runtime_heartbeat(self):
        global _runtime_fork_hooks_registered
        identity = (self.type, self.name)
        with _runtime_lock:
            if not _runtime_fork_hooks_registered:
                os.register_at_fork(
                    before=_before_fork,
                    after_in_parent=_after_fork_parent,
                    after_in_child=_after_fork_child,
                )
                _runtime_fork_hooks_registered = True
            heartbeat = _runtime_heartbeats.get(identity)
            if heartbeat is None or heartbeat.pid != os.getpid():
                heartbeat = RuntimeHeartbeat(self)
                _runtime_heartbeats[identity] = heartbeat
            heartbeat.start()

    def stop_runtime_heartbeat(self):
        with _runtime_lock:
            heartbeat = _runtime_heartbeats.get((self.type, self.name))
        if heartbeat is not None and heartbeat.pid == os.getpid():
            heartbeat.stop()

    def send_runtime_heartbeat(self):
        heartbeat_data = {
            'cpu_load': get_cpu_load(),
            'memory_used': get_memory_usage(),
            'disk_used': get_disk_usage(path=settings.BASE_DIR),
            'sessions': [],
        }
        serializer = StatSerializer(data=heartbeat_data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data.pop('sessions', None)
        serializer.validated_data['terminal'] = self.get_or_register_terminal()
        serializer.save()

    def start_heartbeat(self):
        while True:
            heartbeat_data = {
                'cpu_load': get_cpu_load(),
                'memory_used': get_memory_usage(),
                'disk_used': get_disk_usage(path=settings.BASE_DIR),
                'sessions': [],
            }
            status_serializer = StatSerializer(data=heartbeat_data)
            status_serializer.is_valid()
            status_serializer.validated_data.pop('sessions', None)
            terminal = self.get_or_register_terminal()
            status_serializer.validated_data['terminal'] = terminal

            try:
                status_serializer.save()
                time.sleep(self.interval)
            except Exception:
                print("Save status error, close old connections")
                close_old_connections()
            finally:
                time.sleep(self.interval)

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
            suffix_name=TerminalType.core.label,
            _type=TerminalType.core.value
        )


@Singleton
class CeleryTerminal(BaseTerminal):
    def __init__(self):
        super().__init__(
            suffix_name=TerminalType.celery.label,
            _type=TerminalType.celery.value
        )
