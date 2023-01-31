import abc
import time
import shutil
import psutil
import datetime
import threading
import subprocess
from ..hands import *


class BaseService(object):

    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self._process = None
        self.STOP_TIMEOUT = 10
        self.max_retry = 0
        self.retry = 3
        self.LOG_KEEP_DAYS = 7
        self.EXIT_EVENT = threading.Event()

    @property
    @abc.abstractmethod
    def cmd(self):
        return []

    @property
    @abc.abstractmethod
    def cwd(self):
        return ''

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

    def show_status(self):
        if self.is_running:
            msg = f'{self.name} is running: {self.pid}.'
        else:
            msg = f'{self.name} is stopped.'
            if DEBUG:
                msg = '\033[31m{} is stopped.\033[0m\nYou can manual start it to find the error: \n' \
                      '  $ cd {}\n' \
                      '  $ {}'.format(self.name, self.cwd, ' '.join(self.cmd))

        print(msg)

    # -- log --
    @property
    def log_filename(self):
        return f'{self.name}.log'

    @property
    def log_filepath(self):
        return os.path.join(LOG_DIR, self.log_filename)

    @property
    def log_file(self):
        return open(self.log_filepath, 'a')

    @property
    def log_dir(self):
        return os.path.dirname(self.log_filepath)
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

    # -- process --
    @property
    def process(self):
        if not self._process:
            try:
                self._process = psutil.Process(self.pid)
            except:
                pass
        return self._process

    # -- end process --

    # -- action --
    def open_subprocess(self):
        kwargs = {'cwd': self.cwd, 'stderr': self.log_file, 'stdout': self.log_file}
        self._process = subprocess.Popen(self.cmd, **kwargs)

    def start(self):
        if self.is_running:
            self.show_status()
            return
        self.remove_pid()
        self.open_subprocess()
        self.write_pid()
        self.start_other()

    def start_other(self):
        pass

    def stop(self, force=False):
        if not self.is_running:
            self.show_status()
            # self.remove_pid()
            return

        print(f'Stop service: {self.name}', end='')
        sig = 9 if force else 15
        os.kill(self.pid, sig)

        if self.process is None:
            print("\033[31m No process found\033[0m")
            return
        try:
            self.process.wait(1)
        except:
            pass

        for i in range(self.STOP_TIMEOUT):
            if i == self.STOP_TIMEOUT - 1:
                print("\033[31m Error\033[0m")
            if not self.is_running:
                print("\033[32m Ok\033[0m")
                self.remove_pid()
                break
            else:
                continue

    def watch(self):
        self._check()
        if not self.is_running:
            self._restart()
        self._rotate_log()

    def _check(self):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{now} Check service status: {self.name} -> ", end='')
        if self.process:
            try:
                self.process.wait(1)  # 不wait，子进程可能无法回收
            except:
                pass

        if self.is_running:
            print(f'running at {self.pid}')
        else:
            print(f'stopped at {self.pid}')

    def _restart(self):
        if self.retry > self.max_retry:
            logging.info("Service start failed, exit: {}".format(self.name))
            self.EXIT_EVENT.set()
            return
        self.retry += 1
        logging.info(f'> Find {self.name} stopped, retry {self.retry}, {self.pid}')
        self.start()

    def _rotate_log(self):
        now = datetime.datetime.now()
        _time = now.strftime('%H:%M')
        if _time != '23:59':
            return

        backup_date = now.strftime('%Y-%m-%d')
        backup_log_dir = os.path.join(self.log_dir, backup_date)
        if not os.path.exists(backup_log_dir):
            os.mkdir(backup_log_dir)

        backup_log_path = os.path.join(backup_log_dir, self.log_filename)
        if os.path.isfile(self.log_filepath) and not os.path.isfile(backup_log_path):
            logging.info(f'Rotate log file: {self.log_filepath} => {backup_log_path}')
            shutil.copy(self.log_filepath, backup_log_path)
            with open(self.log_filepath, 'w') as f:
                pass

        to_delete_date = now - datetime.timedelta(days=self.LOG_KEEP_DAYS)
        to_delete_dir = os.path.join(LOG_DIR, to_delete_date.strftime('%Y-%m-%d'))
        if os.path.exists(to_delete_dir):
            logging.info(f'Remove old log: {to_delete_dir}')
            shutil.rmtree(to_delete_dir, ignore_errors=True)
    # -- end action --
