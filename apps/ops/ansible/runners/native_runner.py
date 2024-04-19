import ansible_runner

from ops.ansible.cleaner import cleanup_post_run
from ops.ansible.runners.base import BaseRunner


def run(**kwargs):
    _runner = AnsibleNativeRunner(**kwargs)
    return _runner.run()


class AnsibleNativeRunner(BaseRunner):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @cleanup_post_run
    def run(self):
        ansible_runner.run(
            event_handler=self.get_event_handler(),
            status_handler=self.get_status_handler(),
            **self.runner_params,
        )
