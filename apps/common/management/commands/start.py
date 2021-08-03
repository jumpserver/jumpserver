import os
import abc
import time
import signal
import daemon
import subprocess
import threading
from daemon import pidfile
from django.db.models import TextChoices
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Services(TextChoices):
    gunicorn = 'gunicorn', 'gunicorn'
    daphne = 'daphne', 'daphne'
    celery_ansible = 'celery_ansible', 'celery_ansible'
    celery_default = 'celery_default', 'celery_default'
    beat = 'beat', 'beat'
    flower = 'flower', 'flower'
    web = 'web', 'web'
    celery = 'celery', 'celery'
    task = 'task', 'task'
    all = 'all', 'all'

    @classmethod
    def web_services(cls):
        return [cls.gunicorn, cls.daphne]

    @classmethod
    def celery_services(cls):
        return [cls.celery_ansible, cls.celery_default]

    @classmethod
    def task_services(cls):
        return cls.celery_services() + [cls.beat]

    @classmethod
    def all_services(cls):
        return cls.web_services() + cls.task_services()

    @classmethod
    def get_services(cls, names):
        services = set()
        for name in names:
            method_name = f'{name}_services'
            if hasattr(cls, method_name):
                _services = getattr(cls, method_name)()
            elif hasattr(cls, name):
                _services = [getattr(cls, name)]
            else:
                continue
            services.update(set(_services))
        return services


from apps.jumpserver.const import CONFIG
WORKERS = 4
HTTP_HOST = CONFIG.HTTP_BIND_HOST or '127.0.0.1'
HTTP_PORT = CONFIG.HTTP_LISTEN_PORT or 8080
DEBUG = CONFIG.DEBUG or False
BASE_DIR = os.path.dirname(settings.BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, 'logs')
APPS_DIR = os.path.join(BASE_DIR, 'apps')
TMP_DIR = os.path.join(BASE_DIR, 'tmp')


class BaseService(object):

    def __init__(self, name):
        self.name = name
        self.process = None

    @property
    def is_running(self):
        if self.pid == 0:
            return False
        try:
            os.kill(self.pid, 0)
        except (OSError, ProcessLookupError):
            return False
        else:
            return True

    @property
    @abc.abstractmethod
    def cmd(self):
        return []

    @property
    @abc.abstractmethod
    def cwd(self):
        return ''

    def show_status(self):
        if self.is_running:
            msg = f'{self.name} is running: {self.pid}.'
        else:
            msg = f'{self.name} is stopped.'
        print(msg)

    # -- log --

    @property
    def log_filepath(self):
        return os.path.join(LOG_DIR, f'{self.name}.log')

    # -- end log --

    # -- pid --
    @property
    def pid_filepath(self):
        return os.path.join(TMP_DIR, f'{self.name}.pid')

    @property
    def pid(self):
        if not os.path.isfile(self.pid_filepath):
            return 0
        with open(self.pid_filepath) as f:
            try:
                pid = int(f.read().strip())
            except ValueError:
                pid = 0
        return pid

    def write_pid(self):
        with open(self.pid_filepath, 'w') as f:
            f.write(str(self.process.pid))

    def remove_pid(self):
        if os.path.isfile(self.pid_filepath):
            os.unlink(self.pid_filepath)

    # -- end pid --

    # -- action --

    def open_subprocess(self):
        log_file = open(self.log_filepath, 'a')
        kwargs = {'cwd': self.cwd, 'stderr': log_file, 'stdout': log_file}
        self.process = subprocess.Popen(self.cmd, **kwargs)

    def start(self):
        self.remove_pid()
        self.open_subprocess()
        self.write_pid()

    def stop(self):
        pass

    def watch(self):
        pass

    # -- end action --


class GunicornService(BaseService):

    def __init__(self):
        super().__init__(name='gunicorn')

    @property
    def cmd(self):
        log_format = '%(h)s %(t)s %(L)ss "%(r)s" %(s)s %(b)s '
        bind = f'{HTTP_HOST}:{HTTP_PORT}'
        cmd = [
            'gunicorn', 'jumpserver.wsgi',
            '-b', bind,
            '-k', 'gthread',
            '--threads', '10',
            '-w', str(WORKERS),
            '--max-requests', '4096',
            '--access-logformat', log_format,
            '--access-logfile', '-'
        ]
        if DEBUG:
            cmd.append('--reload')
        return cmd

    @property
    def cwd(self):
        return APPS_DIR


class ServicesUtil(object):

    def __init__(self):
        self.services = []
        self.files_preserve = []
        self.EXIT_EVENT = threading.Event()
        self.DAEMON = False

    def start_services(self, services):
        for service in services:
            service: BaseService
            service.start()
            time.sleep(2)
            self.services.append(service)

        if not self.DAEMON:
            self.show_services_status()
            with self.daemon_context:
                self.watch_services()
        else:
            self.watch_services()

    def stop_services(self):
        for service in self.services:
            service.stop()

    def watch_services(self):
        for service in self.services:
            service.watch()

    def show_services_status(self):
        for service in self.services:
            service.show_status()

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

    def clean_up(self):
        if not self.EXIT_EVENT.is_set():
            self.EXIT_EVENT.set()
        services_dump = [s for s in self.services]
        for service in services_dump:
            service.stop()
            service.process.wait()


class Command(BaseCommand):
    help = 'Start services'

    def add_arguments(self, parser):
        parser.add_argument(
            'services',  nargs='+', choices=Services.values, default=Services.all, help='Service'
        )

    def handle(self, *args, **options):
        service_names = options.get('services')
        services = Services.get_services(service_names)
        ServicesUtil.start_gunicorn()
        print('>>>>>>', options)
        print('>>>>>>', services)
