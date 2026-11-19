import os
from pathlib import Path

from celery.signals import heartbeat_sent, worker_ready, worker_shutdown


_runtime_terminal = None


@heartbeat_sent.connect
def heartbeat(sender, **kwargs):
    worker_name = sender.eventer.hostname.split('@')[0]
    heartbeat_path = Path('/tmp/worker_heartbeat_{}'.format(worker_name))
    heartbeat_path.touch()


@worker_ready.connect
def worker_ready(sender, **kwargs):
    worker_name = sender.hostname.split('@')[0]
    ready_path = Path('/tmp/worker_ready_{}'.format(worker_name))
    ready_path.touch()
    # The default service owns the Celery component heartbeat. An
    # ansible-only worker must not advertise that component as online.
    queues = sender.task_consumer.queues
    if any(queue.name == 'celery' for queue in queues):
        from terminal.startup import CeleryTerminal
        global _runtime_terminal
        _runtime_terminal = (os.getpid(), CeleryTerminal())
        _runtime_terminal[1].start_runtime_heartbeat()


@worker_shutdown.connect
def worker_shutdown(sender, **kwargs):
    global _runtime_terminal
    if _runtime_terminal is not None and _runtime_terminal[0] == os.getpid():
        _runtime_terminal[1].stop_runtime_heartbeat()
        _runtime_terminal = None
    worker_name = sender.hostname.split('@')[0]
    for signal in ['ready', 'heartbeat']:
        path = Path('/tmp/worker_{}_{}'.format(signal, worker_name))
        path.unlink(missing_ok=True)
