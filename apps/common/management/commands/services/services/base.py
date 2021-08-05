from ..hands import *
from ..const import Services


class BaseService(object):
    Services = Services

    def __init__(self, name):
        self.name = name
        self.process = None
        self.STOP_TIMEOUT = 10

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
    def log_filename(self):
        return f'{self.name}.log'

    @property
    def log_filepath(self):
        return os.path.join(LOG_DIR, self.log_filename)

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
        log_file = open(self.log_filepath, 'a')
        kwargs = {'cwd': self.cwd, 'stderr': log_file, 'stdout': log_file}
        self.process = subprocess.Popen(self.cmd, **kwargs)

    def start(self):
        self.remove_pid()
        self.open_subprocess()
        self.write_pid()

    def stop(self, force=True):
        if not self.is_running:
            self.show_status()
            self.remove_pid()
            return

        print(f'Stop service: {self.name}', end='')

        sig = 9 if force else 15
        os.kill(self.pid, sig)

        try:
            self.process.wait(1)
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
        pass

    # -- end action --

