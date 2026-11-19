#!/usr/bin/env python3
"""Service supervision without importing Django."""

import ctypes
import datetime
import json
import logging
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time


logger = logging.getLogger('jms.supervisor')


class Supervisor:
    def __init__(self, services, stop_timeout=120):
        self.services = services
        self.stop_timeout = stop_timeout
        self.children = []
        self.stopping = False
        self.rotated_date = None

    def request_stop(self, signum, frame):
        self.stopping = True

    def become_subreaper(self):
        # Adopt and reap descendants if their immediate parent exits first.
        if sys.platform == 'linux':
            libc = ctypes.CDLL(None, use_errno=True)
            if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
                raise OSError(ctypes.get_errno(), 'Cannot become child subreaper')

    def start(self):
        for service in self.services:
            if self.stopping:
                break
            log_path = Path(service['log_path'])
            pid_path = Path(service['pid_path'])
            log_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open('ab', buffering=0) as output:
                process = subprocess.Popen(
                    service['cmd'], cwd=service['cwd'], stdout=output,
                    stderr=subprocess.STDOUT, start_new_session=True,
                )
            self.children.append((service, process))
            pid_path.write_text(str(process.pid))
            logger.info('Started %s pid=%s', service['name'], process.pid)

    def reap(self):
        managed = {process.pid: process for _, process in self.children}
        while True:
            try:
                pid, status = os.waitpid(-1, os.WNOHANG)
            except ChildProcessError:
                return
            if not pid:
                return
            if pid in managed:
                managed[pid].returncode = os.waitstatus_to_exitcode(status)

    def rotate_logs(self):
        now = datetime.datetime.now()
        if now.strftime('%H:%M') != '23:59' or self.rotated_date == now.date():
            return
        for service, _ in self.children:
            source = Path(service['log_path'])
            target = source.parent / now.strftime('%Y-%m-%d') / source.name
            if source.exists() and not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                with source.open('r+b') as stream:
                    stream.truncate(0)
            expired = source.parent / (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
            if expired.is_dir():
                shutil.rmtree(expired, ignore_errors=True)
        self.rotated_date = now.date()

    @staticmethod
    def signal_group(process, signum):
        try:
            os.killpg(process.pid, signum)
        except ProcessLookupError:
            pass

    def stop(self):
        # Stop scheduling first. Signal leaders so workers can finish in-flight tasks.
        children = sorted(self.children, key=lambda item: item[0]['name'] != 'beat')
        for service, process in children:
            if process.returncode is None:
                try:
                    os.kill(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
        deadline = time.monotonic() + self.stop_timeout
        while any(p.returncode is None for _, p in children) and time.monotonic() < deadline:
            self.reap()
            time.sleep(0.1)
        for service, process in children:
            # Clear any descendants left after their leader has stopped.
            self.signal_group(process, signal.SIGTERM)
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            self.reap()
            time.sleep(0.1)
        for service, process in children:
            self.signal_group(process, signal.SIGKILL)
        for service, process in children:
            if process.returncode is None:
                process.wait()
            path = Path(service['pid_path'])
            try:
                if path.read_text().strip() == str(process.pid):
                    path.unlink()
            except FileNotFoundError:
                pass
        self.reap()

    def run(self):
        self.become_subreaper()
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
            signal.signal(signum, self.request_stop)
        exit_code = 0
        try:
            self.start()
            while not self.stopping:
                self.reap()
                exited = [(s, p) for s, p in self.children if p.returncode is not None]
                if exited:
                    for service, process in exited:
                        logger.error('%s exited with status %s', service['name'], process.returncode)
                    exit_code = 1
                    break
                try:
                    self.rotate_logs()
                except OSError:
                    logger.exception('Log rotation failed; services remain running')
                time.sleep(0.2)
        except Exception:
            logger.exception('Service supervision failed')
            exit_code = 1
        finally:
            self.stop()
        return exit_code


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    path = Path(sys.argv[1])
    try:
        plan = json.loads(path.read_text())
    finally:
        path.unlink()
    if not plan['services']:
        raise ValueError('No services to supervise')
    supervisor = Supervisor(plan['services'])
    daemon_plan = plan.get('daemon')
    if not daemon_plan:
        return supervisor.run()

    import daemon
    from daemon.pidfile import TimeoutPIDLockFile

    pid_path = Path(daemon_plan['pid_path'])
    log_path = Path(daemon_plan['log_path'])
    pid_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    pid_lock = TimeoutPIDLockFile(str(pid_path), acquire_timeout=0)
    if pid_lock.is_locked():
        pid = pid_lock.read_pid()
        if pid and pid > 0:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError(f'JumpServer daemon is already running: {pid}')
        pid_lock.break_lock()
    with log_path.open('a') as output:
        with daemon.DaemonContext(
            pidfile=pid_lock, stdout=output, stderr=output,
            signal_map={
                signum: supervisor.request_stop
                for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT)
            },
            detach_process=True,
        ):
            return supervisor.run()


if __name__ == '__main__':
    sys.exit(main())
