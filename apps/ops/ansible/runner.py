import os
import shutil
import uuid

from django.conf import settings
from django.utils._os import safe_join

from common.utils import is_macos
from .callback import DefaultCallback
from .exception import CommandInBlackListException
from .interface import interface
from ..utils import get_ansible_log_verbosity

__all__ = ['AdHocRunner', 'PlaybookRunner', 'SuperPlaybookRunner', 'UploadFileRunner']


class AdHocRunner:
    cmd_modules_choices = ('shell', 'raw', 'command', 'script', 'win_shell')
    need_local_connection_modules_choices = ("mysql", "postgresql", "sqlserver", "huawei")

    def __init__(self, inventory, job_module, module, module_args='', pattern='*', project_dir='/tmp/',
                 extra_vars=None,
                 dry_run=False, timeout=-1):
        if extra_vars is None:
            extra_vars = {}
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.pattern = pattern
        self.module = module
        self.job_module = job_module
        self.module_args = module_args
        self.project_dir = project_dir
        self.cb = DefaultCallback()
        self.runner = None
        self.extra_vars = extra_vars
        self.dry_run = dry_run
        self.timeout = timeout
        self.envs = {}

    def check_module(self):
        if self.module not in self.cmd_modules_choices:
            return
        if self.module_args and self.module_args.split()[0] in settings.SECURITY_COMMAND_BLACKLIST:
            raise CommandInBlackListException(
                "Command is rejected by black list: {}".format(self.module_args.split()[0]))

    def set_local_connection(self):
        if self.job_module in self.need_local_connection_modules_choices:
            self.envs.update({"ANSIBLE_SUPER_MODE": "1"})

    def run(self, verbosity=0, **kwargs):
        self.check_module()
        self.set_local_connection()
        verbosity = get_ansible_log_verbosity(verbosity)

        if not os.path.exists(self.project_dir):
            os.mkdir(self.project_dir, 0o755)
        private_env = safe_join(self.project_dir, 'env')
        if os.path.exists(private_env):
            shutil.rmtree(private_env)

        interface.run(
            timeout=self.timeout if self.timeout > 0 else None,
            extravars=self.extra_vars,
            envvars=self.envs,
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
        self.isolate = True
        self.envs = {}

    def copy_playbook(self):
        entry = os.path.basename(self.playbook)
        playbook_dir = os.path.dirname(self.playbook)
        project_playbook_dir = os.path.join(self.project_dir, "project")
        shutil.copytree(playbook_dir, project_playbook_dir, dirs_exist_ok=True)
        self.playbook = entry

    def run(self, verbosity=0, **kwargs):
        self.copy_playbook()

        verbosity = get_ansible_log_verbosity(verbosity)
        private_env = safe_join(self.project_dir, 'env')
        if os.path.exists(private_env):
            shutil.rmtree(private_env)

        kwargs = dict(kwargs)
        if self.isolate and not is_macos():
            kwargs['process_isolation'] = True
            kwargs['process_isolation_executable'] = 'bwrap'

        interface.run(
            private_data_dir=self.project_dir,
            inventory=self.inventory,
            playbook=self.playbook,
            verbosity=verbosity,
            event_handler=self.cb.event_handler,
            status_handler=self.cb.status_handler,
            host_cwd=self.project_dir,
            envvars=self.envs,
            **kwargs
        )
        return self.cb


class SuperPlaybookRunner(PlaybookRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.envs = {"ANSIBLE_SUPER_MODE": "1"}
        self.isolate = False


class UploadFileRunner:
    def __init__(self, inventory, project_dir, job_id, dest_path, callback=None):
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.project_dir = project_dir
        self.cb = DefaultCallback()
        upload_file_dir = safe_join(settings.SHARE_DIR, 'job_upload_file')
        self.src_paths = safe_join(upload_file_dir, str(job_id))
        self.dest_path = safe_join("/tmp", dest_path)

    def run(self, verbosity=0, **kwargs):
        verbosity = get_ansible_log_verbosity(verbosity)
        interface.run(
            private_data_dir=self.project_dir,
            host_pattern="*",
            inventory=self.inventory,
            module='copy',
            module_args=f"src={self.src_paths}/ dest={self.dest_path}",
            verbosity=verbosity,
            event_handler=self.cb.event_handler,
            status_handler=self.cb.status_handler,
            **kwargs
        )
        try:
            shutil.rmtree(self.src_paths)
        except OSError as e:
            print(f"del upload tmp dir {self.src_paths} failed! {e}")
        return self.cb
