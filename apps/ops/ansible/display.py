import errno
import sys
import os

from ansible.utils.display import Display
from ansible.utils.color import stringc
from ansible.utils.singleton import Singleton

from .utils import get_ansible_task_log_path


class UnSingleton(Singleton):
    def __init__(cls, name, bases, dct):
        type.__init__(cls, name, bases, dct)

    def __call__(cls, *args, **kwargs):
        return type.__call__(cls, *args, **kwargs)


class AdHocDisplay(Display, metaclass=UnSingleton):
    def __init__(self, execution_id, verbosity=0):
        super().__init__(verbosity=verbosity)
        if execution_id:
            log_path = get_ansible_task_log_path(execution_id)
        else:
            log_path = os.devnull
        self.log_file = open(log_path, mode='a')

    def close(self):
        self.log_file.close()

    def set_cowsay_info(self):
        # 中断 cowsay 的测试，会频繁开启子进程
        return

    def _write_to_screen(self, msg, stderr):
        if not stderr:
            screen = sys.stdout
        else:
            screen = sys.stderr

        screen.write(msg)

        try:
            screen.flush()
        except IOError as e:
            # Ignore EPIPE in case fileobj has been prematurely closed, eg.
            # when piping to "head -n1"
            if e.errno != errno.EPIPE:
                raise

    def _write_to_log_file(self, msg):
        # 这里先不 flush，log 文件不需要那么及时。
        self.log_file.write(msg)

    def display(self, msg, color=None, stderr=False, screen_only=False, log_only=False):
        if color:
            msg = stringc(msg, color)

        if not msg.endswith(u'\n'):
            msg2 = msg + u'\n'
        else:
            msg2 = msg

        self._write_to_screen(msg2, stderr)
        self._write_to_log_file(msg2)
