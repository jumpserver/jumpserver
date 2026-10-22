import json
import os
from pathlib import Path
import threading
import uuid

from django.conf import settings

from ops.ansible.cleaner import cleanup_post_run
from .base import BaseRunner

_running = {}
_lock = threading.Lock()


def cancel_ssh_job(job_id):
    with _lock:
        event = _running.get(str(job_id))
        if event:
            event.set()


def localize_event(data, root):
    # DefaultCallback may inspect task_path to infer ignore_unreachable. A remote
    # task must never make it open an arbitrary path on the Celery filesystem.
    payload = data.get('event_data', {})
    task_path = payload.get('task_path')
    if not isinstance(task_path, str):
        return data
    project = (root / 'project').resolve()
    path, separator, line = task_path.rpartition(':')
    _, marker, relative = path.partition('/project/')
    local = (project / relative).resolve()
    if separator and line.isdecimal() and marker and local.is_relative_to(project):
        payload['task_path'] = f'{local}:{line}'
    else:
        payload.pop('task_path', None)
    return data


class AnsibleSSHRunner(BaseRunner):
    @cleanup_post_run
    def run(self):
        from jms_ansible_executor.client import run

        job_id = str(uuid.uuid4())
        canceled = threading.Event()
        params = dict(self.runner_params)
        # SSH workers do not inherit Core's forced-color setting.
        params['envvars'] = {
            'ANSIBLE_FORCE_COLOR': os.environ['ANSIBLE_FORCE_COLOR'],
            **(params.get('envvars') or {}),
        }
        event_handler = self.get_event_handler()
        status_handler = self.get_status_handler()
        params.pop('event_handler', None)
        params.pop('status_handler', None)
        cancel_callback = params.pop('cancel_callback', None)
        job_timeout = params.get('timeout')
        if job_timeout is None:
            job_timeout = settings.ANSIBLE_RUNNER_JOB_TIMEOUT
        with _lock:
            _running[job_id] = canceled
        try:
            root = Path(self.private_data_dir)
            root.mkdir(mode=0o700, parents=True, exist_ok=True)
            metadata = root / 'remote.json'
            # Created before connecting, so cancellation also works during upload/auth.
            pending = root / f'.remote-{job_id}.json'
            fd = os.open(pending, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            try:
                with os.fdopen(fd, 'w') as output:
                    json.dump({'backend': 'ssh', 'job_id': job_id}, output)
                os.replace(pending, metadata)
            finally:
                pending.unlink(missing_ok=True)
            cancel_file = root / f'cancel-{job_id}'
            return run(
                host=settings.ANSIBLE_EXECUTOR_HOST,
                port=settings.ANSIBLE_EXECUTOR_PORT,
                private_key=settings.ANSIBLE_EXECUTOR_PRIVATE_KEY,
                known_hosts=settings.ANSIBLE_EXECUTOR_KNOWN_HOSTS,
                connect_timeout=settings.ANSIBLE_EXECUTOR_CONNECT_TIMEOUT,
                job_timeout=job_timeout,
                event_handler=(lambda data: event_handler(localize_event(data, root))) if event_handler else None,
                status_handler=status_handler,
                cancel_callback=lambda: (canceled.is_set() or cancel_file.exists()
                                         or bool(cancel_callback and cancel_callback())),
                job_id=job_id, **params,
            )
        finally:
            with _lock:
                _running.pop(job_id, None)
