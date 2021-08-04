from .hands import *
from .hands import __version__
from .services.base import BaseService


class ServicesUtil(object):

    def __init__(self):
        self.process_services = {}
        self.stopped_services = {}
        self.services_retry = defaultdict(int)
        self.max_retry = 3
        self.files_preserve = []
        self.EXIT_EVENT = threading.Event()
        self.LOCK = threading.Lock()

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
            if service.is_running:
                service.show_status()
                continue
            service.start()
            time.sleep(2)
            self.process_services[service.name] = service

    def stop(self, services, force=True, stop_daemon=False):
        for service in services:
            service: BaseService
            service.stop(force=force)

        if stop_daemon:
            self.stop_daemon()

    def __check_processes(self):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for name, service in self.process_services.items():
            service: BaseService
            print(f"{now} Check service status: {service.name} -> ", end='')
            try:
                service.process.wait(timeout=1)  # 不wait，子进程可能无法回收
            except subprocess.TimeoutExpired:
                pass
            if service.is_running:
                print(f'running at {service.process.pid}')
                self.stopped_services.pop(name, None)
                self.services_retry.pop(name, None)
            else:
                self.stopped_services[name] = service
                print(f'stopped with code: {service.process.returncode}({service.process.pid})')

    def __restart_for_stopped(self):
        for name, service in self.stopped_services.items():
            retry = self.services_retry[name]
            if retry > self.max_retry:
                logging.info("Service start failed, exit: ", name)
                self.EXIT_EVENT.set()
                continue
            service.start()
            logging.info(f'> Find {name} stopped, retry {retry+1}, {service.process.pid}')
            self.services_retry[name] += 1

    def __rotate_log(self):
        pass

    def watch(self):
        while not self.EXIT_EVENT.is_set():
            try:
                with self.LOCK:
                    self.__check_processes()
                if self.stopped_services:
                    self.__restart_for_stopped()
                self.__rotate_log()
                time.sleep(30)
            except KeyboardInterrupt:
                print("Start stop service")
                time.sleep(1)
                break
        self.clean_up()

    def clean_up(self):
        if not self.EXIT_EVENT.is_set():
            self.EXIT_EVENT.set()
        process_services = {name: service for name, service in self.process_services.items()}
        for name, service in process_services.items():
            service.stop()
            service.process.wait()
            self.process_services.pop(service.name, None)

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
            files_preserve=self.files_preserve,
            detach_process=True,
        )
        return context
    # -- end daemon --
