import uuid
import ansible_runner

from django.conf import settings


class AdHocRunner:
    cmd_modules_choices = ('shell', 'raw', 'command', 'script', 'win_shell')
    cmd_blacklist = [
        "reboot", 'shutdown', 'poweroff', 'halt', 'dd', 'half', 'top'
    ]

    def __init__(self, inventory, module, module_args, pattern='*', project_dir='/tmp/'):
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.pattern = pattern
        self.module = module
        self.module_args = module_args
        self.project_dir = project_dir

    def check_module(self):
        if self.module not in self.cmd_modules_choices:
            return
        if self.module_args and self.module_args.split()[0] in self.cmd_blacklist:
            raise Exception("command not allowed: {}".format(self.module_args[0]))

    def run(self, verbosity=0, **kwargs):
        self.check_module()
        if verbosity is None and settings.DEBUG:
            verbosity = 1

        return ansible_runner.run(
            host_pattern=self.pattern,
            private_data_dir=self.project_dir,
            inventory=self.inventory,
            module=self.module,
            module_args=self.module_args,
            verbosity=verbosity,
            **kwargs
        )


class PlaybookRunner:
    pass
