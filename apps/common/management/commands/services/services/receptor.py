from .base import BaseService
from ..hands import *

__all__ = ['ReceptorService']

ANSIBLE_RUNNER_COMMAND = "ansible-runner"


class ReceptorService(BaseService):
    @property
    def cmd(self):
        print("\n- Start Receptor as Ansible Runner Sandbox")

        cmd = [
            'receptor',
            '--local-only',
            '--node', 'id=primary',
            '--control-service',
            'service=control',
            'filename=/opt/jumpserver/share/control.sock',
            '--work-command',
            'worktype={}'.format(ANSIBLE_RUNNER_COMMAND),
            'command={}'.format(ANSIBLE_RUNNER_COMMAND),
            'params=worker',
            'allowruntimeparams=true'
        ]

        return cmd

    @property
    def cwd(self):
        return APPS_DIR
