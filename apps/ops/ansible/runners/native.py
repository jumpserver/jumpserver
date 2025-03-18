import ansible_runner

from libs.process.ssh import kill_ansible_ssh_process
from ops.ansible.cleaner import cleanup_post_run
from ops.ansible.runners.base import BaseRunner

__all__ = ['AnsibleNativeRunner']


class AnsibleNativeRunner(BaseRunner):
    @classmethod
    def kill_precess(cls, pid):
        return kill_ansible_ssh_process(pid)

    @cleanup_post_run
    def run(self):
        ansible_runner.run(
            event_handler=self.get_event_handler(),
            status_handler=self.get_status_handler(),
            **self.runner_params,
        )
