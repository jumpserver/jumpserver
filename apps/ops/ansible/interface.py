from django.conf import settings
from django.utils.functional import LazyObject

from ops.ansible import AnsibleNativeRunner
from ops.ansible.runners.base import BaseRunner
from ops.ansible.execution import use_ansible_ssh_executor
from ops.ansible.runners.ssh import AnsibleSSHRunner, cancel_ssh_job

__all__ = ['interface']


class _LazyRunnerInterface(LazyObject):

    def _setup(self):
        self._wrapped = self.make_interface()

    @staticmethod
    def make_interface():
        runner_type = AnsibleNativeRunner
        return RunnerInterface(runner_type=runner_type, gateway_proxy_host='127.0.0.1')


interface = _LazyRunnerInterface()


class RunnerInterface:
    def __init__(self, runner_type, gateway_proxy_host='127.0.0.1'):
        if not issubclass(runner_type, BaseRunner):
            raise TypeError(f'{runner_type} can not cast to {BaseRunner}')
        self._runner_type = runner_type
        self._gateway_proxy_host = gateway_proxy_host

    def get_gateway_proxy_host(self):
        if use_ansible_ssh_executor():
            host = settings.ANSIBLE_EXECUTOR_GATEWAY_HOST
            if not host or host in ('127.0.0.1', 'localhost', '::1'):
                raise ValueError('ANSIBLE_EXECUTOR_GATEWAY_HOST must be reachable from the executor')
            return host
        return self._gateway_proxy_host

    def get_runner_type(self):
        if use_ansible_ssh_executor():
            return AnsibleSSHRunner
        return self._runner_type

    def kill_process(self, pid):
        if isinstance(pid, dict) and pid.get('backend') == 'ssh':
            return cancel_ssh_job(pid.get('job_id'))
        return self._runner_type.kill_precess(pid)

    def run(self, **kwargs):
        runner_type = self.get_runner_type()
        runner = runner_type(**kwargs)
        return runner.run()
