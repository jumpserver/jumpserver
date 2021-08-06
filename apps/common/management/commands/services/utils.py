from .hands import *
from .hands import __version__
from .services.base import BaseService


class ServicesUtil(object):

    def __init__(self):
        self.services_map = {}
        self.files_preserve_map = {}
        self.EXIT_EVENT = threading.Event()
        self.check_interval = 5

    def restart(self, services, stop_daemon=False):
        self.stop(services=services, stop_daemon=stop_daemon)
        time.sleep(5)
        self.start_and_watch(services, _daemon=True)

    def start_and_watch(self, services, _daemon=False):
        logging.info(time.ctime())
        logging.info(f'JumpServer version {__version__}, more see https://www.jumpserver.org')
        self.start(services)
        if _daemon:
            self.show_status(services)
            with self.daemon_context:
                self.watch()
        else:
            self.watch()

    def start(self, services):
        for service in services:
            service: BaseService
            service.start()
            self.files_preserve_map[service.name] = service.log_file
            time.sleep(1)
            self.services_map[service.name] = service

    def stop(self, services, force=True, stop_daemon=False):
        for service in services:
            service: BaseService
            service.stop(force=force)

        if stop_daemon:
            self.stop_daemon()

    # -- watch --
    def watch(self):
        while not self.EXIT_EVENT.is_set():
            try:
                go_on = self._watch()
                if not go_on:
                    break
                time.sleep(self.check_interval)
            except KeyboardInterrupt:
                print('Start stop services')
                break

        self.clean_up()

    def _watch(self):
        for name, service in self.services_map.items():
            service: BaseService
            service.watch()
            if service.EXIT_EVENT.is_set():
                self.EXIT_EVENT.set()
                return False
        return True
    # -- end watch --

    def clean_up(self):
        if not self.EXIT_EVENT.is_set():
            self.EXIT_EVENT.set()
        for name, service in self.services_map.items():
            service: BaseService
            service.stop()

    def show_status(self, services):
        for service in services:
            service: BaseService
            service.show_status()

    # -- daemon --
    def stop_daemon(self):
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
