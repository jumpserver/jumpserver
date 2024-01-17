from .base import BaseService
from ..hands import *


class CeleryBaseService(BaseService):

    def __init__(self, queue, num=10, **kwargs):
        super().__init__(**kwargs)
        self.queue = queue
        self.num = num

    @property
    def cmd(self):
        print('\n- Start Celery as Distributed Task Queue: {}'.format(self.queue.capitalize()))
        ansible_config_path = os.path.join(settings.APPS_DIR, 'ops', 'ansible', 'ansible.cfg')
        ansible_modules_path = os.path.join(settings.APPS_DIR, 'ops', 'ansible', 'modules')
        os.environ.setdefault('LC_ALL', 'C.UTF-8')
        os.environ.setdefault('PYTHONOPTIMIZE', '1')
        os.environ.setdefault('ANSIBLE_FORCE_COLOR', 'True')
        os.environ.setdefault('ANSIBLE_CONFIG', ansible_config_path)
        os.environ.setdefault('ANSIBLE_LIBRARY', ansible_modules_path)
        os.environ.setdefault('PYTHONPATH', settings.APPS_DIR)

        if os.getuid() == 0:
            os.environ.setdefault('C_FORCE_ROOT', '1')
        server_hostname = os.environ.get("SERVER_HOSTNAME")
        if not server_hostname:
            server_hostname = '%h'

        cmd = [
            'celery',
            '-A', 'ops',
            'worker',
            '-P', 'threads',
            '-l', 'INFO',
            '-c', str(self.num),
            '-Q', self.queue,
            '--heartbeat-interval', '10',
            '-n', f'{self.queue}@{server_hostname}',
            '--without-mingle',
        ]
        return cmd

    @property
    def cwd(self):
        return APPS_DIR
