__all__ = ['RunnerInterface']

from ops.ansible.runners.base import BaseRunner


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
