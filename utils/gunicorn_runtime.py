"""Worker-only component heartbeat hooks for the lightweight supervisor."""

import os


def post_worker_init(worker):
    # Gunicorn has loaded the ASGI application and initialized Django here.
    # Keep these imports inside the child hook so the master stays lightweight.
    from terminal.startup import CoreTerminal

    terminal = CoreTerminal()
    terminal.start_runtime_heartbeat()
    worker._jms_runtime_terminal = terminal


def worker_exit(server, worker):
    # Gunicorn can also call worker_exit in the master when reaping a worker.
    # Never import Django or touch another process's heartbeat from that path.
    if worker.pid != os.getpid():
        return
    terminal = getattr(worker, '_jms_runtime_terminal', None)
    if terminal is not None:
        terminal.stop_runtime_heartbeat()
