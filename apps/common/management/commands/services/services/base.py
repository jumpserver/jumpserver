from ..hands import *
from ..const import Services


class BaseService(object):
    Services = Services

    def __init__(self, **kwargs):
        self.name = kwargs['name']
        self.process = None
        self.STOP_TIMEOUT = 10
        self.max_retry = 3
        self.retry = 0
        self.EXIT_EVENT = threading.Event()
        self.LOCK = threading.Lock()

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

    # -- action --
    def open_subprocess(self):
        kwargs = {'cwd': self.cwd, 'stderr': self.log_file, 'stdout': self.log_file}
        self.process = subprocess.Popen(self.cmd, **kwargs)

    def start(self):
        self.remove_pid()
        self.open_subprocess()
        self.write_pid()
        self.start_other()

    def start_other(self):
        pass

    def stop(self, force=True):
        if not self.is_running:
            self.show_status()
            self.remove_pid()
            return

        print(f'Stop service: {self.name}', end='')

        sig = 9 if force else 15
        os.kill(self.pid, sig)

        try:
            self.process.wait(2)
        except:
            pass

        for i in range(self.STOP_TIMEOUT):
            if i == self.STOP_TIMEOUT - 1:
                print("\033[31m Error\033[0m")
            if not self.is_running:
                print("\033[32m Ok\033[0m")
                break
            else:
                time.sleep(1)
                continue

        self.remove_pid()

    def watch(self):
        with self.LOCK:
            self.__check()
        if not self.is_running:
            self.__restart()
        self.__rotate_log()

    def __check(self):
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"{now} Check service status: {self.name} -> ", end='')
        try:
            self.process.wait(timeout=1)  # 不wait，子进程可能无法回收
        except subprocess.TimeoutExpired:
            pass
        if self.is_running:
            print(f'running at {self.process.pid}')
        else:
            print(f'stopped with code: {self.process.returncode}({self.process.pid})')

    def __restart(self):
        if self.retry > self.max_retry:
            logging.info("Service start failed, exit: ", self.name)
            self.EXIT_EVENT.set()
            return
        self.start()
        self.retry += 1
        logging.info(f'> Find {self.name} stopped, retry {self.retry}, {self.process.pid}')

    def __rotate_log(self):
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

        to_delete_date = now - datetime.timedelta(days=LOG_KEEP_DAYS)
        to_delete_dir = os.path.join(LOG_DIR, to_delete_date.strftime('%Y-%m-%d'))
        if os.path.exists(to_delete_dir):
            logging.info(f'Remove old log: {to_delete_dir}')
            shutil.rmtree(to_delete_dir, ignore_errors=True)
    # -- end action --

