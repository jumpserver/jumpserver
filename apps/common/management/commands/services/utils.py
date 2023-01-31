import threading
import signal
import time
import daemon
from daemon import pidfile
from .hands import *
from .hands import __version__
from .services.base import BaseService


class ServicesUtil(object):

    def __init__(self, services, run_daemon=False, force_stop=False, stop_daemon=False):
        self._services = services
        self.run_daemon = run_daemon
        self.force_stop = force_stop
        self.stop_daemon = stop_daemon
        self.EXIT_EVENT = threading.Event()
        self.check_interval = 30
        self.files_preserve_map = {}

    def restart(self):
        self.stop()
        time.sleep(5)
        self.start_and_watch()

    def start_and_watch(self):
        logging.info(time.ctime())
        logging.info(f'JumpServer version {__version__}, more see https://www.jumpserver.org')
        self.start()
        if self.run_daemon:
            self.show_status()
            with self.daemon_context:
                self.watch()
        else:
            self.watch()

    def start(self):
        for service in self._services:
            service: BaseService
            service.start()
            self.files_preserve_map[service.name] = service.log_file

        time.sleep(1)

    def stop(self):
        for service in self._services:
            service: BaseService
            service.stop(force=self.force_stop)

        if self.stop_daemon:
            self._stop_daemon()

    # -- watch --
    def watch(self):
        while not self.EXIT_EVENT.is_set():
            try:
                _exit = self._watch()
                if _exit:
                    break
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print('Start stop services')
                break
        self.clean_up()

    def _watch(self):
        for service in self._services:
            service: BaseService
            service.watch()
            if service.EXIT_EVENT.is_set():
                self.EXIT_EVENT.set()
                return True
        return False
    # -- end watch --

    def clean_up(self):
        if not self.EXIT_EVENT.is_set():
            self.EXIT_EVENT.set()
        self.stop()

    def show_status(self):
        for service in self._services:
            service: BaseService
            service.show_status()

    # -- daemon --
    def _stop_daemon(self):
        if self.daemon_pid and self.daemon_is_running:
            os.kill(self.daemon_pid, 15)
        self.remove_daemon_pid()

    def remove_daemon_pid(self):
        if os.path.isfile(self.daemon_pid_filepath):
            os.unlink(self.daemon_pid_filepath)

    @property
    def daemon_pid(self):
        if not os.path.isfile(self.daemon_pid_filepath):
            return 0
        with open(self.daemon_pid_filepath) as f:
            try:
                pid = int(f.read().strip())
            except ValueError:
                pid = 0
        return pid

    @property
    def daemon_is_running(self):
        try:
            os.kill(self.daemon_pid, 0)
        except (OSError, ProcessLookupError):
            return False
        else:
            return True

    @property
    def daemon_pid_filepath(self):
        return os.path.join(TMP_DIR, 'jms.pid')

    @property
    def daemon_log_filepath(self):
        return os.path.join(LOG_DIR, 'jms.log')

    @property
    def daemon_context(self):
        daemon_log_file = open(self.daemon_log_filepath, 'a')
        context = daemon.DaemonContext(
            pidfile=pidfile.TimeoutPIDLockFile(self.daemon_pid_filepath),
            signal_map={
                signal.SIGTERM: lambda x, y: self.clean_up(),
                signal.SIGHUP: 'terminate',
            },
            stdout=daemon_log_file,
            stderr=daemon_log_file,
            files_preserve=list(self.files_preserve_map.values()),
            detach_process=True,
        )
        return context
    # -- end daemon --
