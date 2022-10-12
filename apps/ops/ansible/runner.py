import uuid
import os

import ansible_runner
from django.conf import settings

from .callback import DefaultCallback


class AdHocRunner:
    cmd_modules_choices = ('shell', 'raw', 'command', 'script', 'win_shell')
    cmd_blacklist = [
        "reboot", 'shutdown', 'poweroff', 'halt', 'dd', 'half', 'top'
    ]

    def __init__(self, inventory, module, module_args='', pattern='*', project_dir='/tmp/'):
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.pattern = pattern
        self.module = module
        self.module_args = module_args
        self.project_dir = project_dir
        self.cb = DefaultCallback()
        self.runner = None

    def check_module(self):
        if self.module not in self.cmd_modules_choices:
            return
        if self.module_args and self.module_args.split()[0] in self.cmd_blacklist:
            raise Exception("command not allowed: {}".format(self.module_args[0]))

    def run(self, verbosity=0, **kwargs):
        self.check_module()
        if verbosity is None and settings.DEBUG:
            verbosity = 1

        if not os.path.exists(self.project_dir):
            os.mkdir(self.project_dir, 0o755)

        ansible_runner.run(
            host_pattern=self.pattern,
            private_data_dir=self.project_dir,
            inventory=self.inventory,
            module=self.module,
            module_args=self.module_args,
            verbosity=verbosity,
            event_handler=self.cb.event_handler,
            status_handler=self.cb.status_handler,
            **kwargs
        )
        return self.cb


class PlaybookRunner:
    def __init__(self, inventory, playbook, project_dir='/tmp/', callback=None):
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.playbook = playbook
        self.project_dir = project_dir
        if not callback:
            callback = DefaultCallback()
        self.cb = callback

    def run(self, verbosity=0, **kwargs):
        if verbosity is None and settings.DEBUG:
            verbosity = 1

        ansible_runner.run(
            private_data_dir=self.project_dir,
            inventory=self.inventory,
            playbook=self.playbook,
            verbosity=verbosity,
            event_handler=self.cb.event_handler,
            status_handler=self.cb.status_handler,
            **kwargs
        )
        return self.cb


class CommandRunner(AdHocRunner):
    def __init__(self, inventory, command, pattern='*', project_dir='/tmp/'):
        super().__init__(inventory, 'shell', command, pattern, project_dir)

    def run(self, verbosity=0, **kwargs):
        return super().run(verbosity, **kwargs)
