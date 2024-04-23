from django.conf import settings
from django.utils.functional import LazyObject

from ops.ansible import AnsibleReceptorRunner, AnsibleNativeRunner
from ops.ansible.runners.base import BaseRunner

__all__ = ['interface']


class _LazyRunnerInterface(LazyObject):

    def _setup(self):
        self._wrapped = self.make_interface()

    @staticmethod
    def make_interface():
        runner_type = AnsibleReceptorRunner \
            if settings.RECEPTOR_ENABLED else AnsibleNativeRunner
        gateway_host = settings.ANSIBLE_RECEPTOR_GATEWAY_PROXY_HOST \
            if settings.ANSIBLE_RECEPTOR_GATEWAY_PROXY_HOST else '127.0.0.1'
        return RunnerInterface(runner_type=runner_type, gateway_proxy_host=gateway_host)


interface = _LazyRunnerInterface()


class RunnerInterface:
    def __init__(self, runner_type, gateway_proxy_host='127.0.0.1'):
        if not issubclass(runner_type, BaseRunner):
            raise TypeError(f'{runner_type} can not cast to {BaseRunner}')
        self._runner_type = runner_type
        self._gateway_proxy_host = gateway_proxy_host

    def get_gateway_proxy_host(self):
        return self._gateway_proxy_host

    def get_runner_type(self):
        return self._runner_type

    def kill_process(self, pid):
        return self._runner_type.kill_precess(pid)

    def run(self, **kwargs):
        runner_type = self.get_runner_type()
        runner = runner_type(**kwargs)
        return runner.run()
