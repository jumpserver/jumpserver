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

ANSIBLE_EE_IMAGE = 'jms_ansible_ee:latest'


def use_ansible_docker_isolation():
    """Production runs ansible in EE container; dev runs in celery worker."""
    return not settings.DEBUG_DEV


def docker_isolation_kwargs():
    return {
        'process_isolation': True,
        'process_isolation_executable': 'docker',
        'container_image': ANSIBLE_EE_IMAGE,
        'container_options': ['--network=host'],
    }


def prepare_isolated_ansible_cfg(project_dir):
    """Copy ansible.cfg into job dir so the EE container picks up SSH settings."""
    if not use_ansible_docker_isolation():
        return
    src = os.path.join(settings.APPS_DIR, 'libs', 'ansible', 'ansible.cfg')
    dst = os.path.join(project_dir, 'ansible.cfg')
    shutil.copyfile(src, dst)


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
        command = self.module_args
        if command and set(command.split()).intersection(set(settings.SECURITY_COMMAND_BLACKLIST)):
            raise CommandInBlackListException(
                "Command is rejected by black list: {}".format(self.module_args))

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

        prepare_isolated_ansible_cfg(self.project_dir)

        run_kwargs = {
            'timeout': self.timeout if self.timeout > 0 else None,
            'extravars': self.extra_vars,
            'envvars': self.envs,
            'host_pattern': self.pattern,
            'private_data_dir': self.project_dir,
            'inventory': self.inventory,
            'module': self.module,
            'module_args': self.module_args,
            'verbosity': verbosity,
            'event_handler': self.cb.event_handler,
            'status_handler': self.cb.status_handler,
            **kwargs,
        }
        if use_ansible_docker_isolation():
            run_kwargs.update(docker_isolation_kwargs())

        interface.run(**run_kwargs)
        return self.cb


class PlaybookRunner:
    def __init__(self, inventory, playbook, project_dir='/tmp/', callback=None, extra_vars=None, ):

        self.id = uuid.uuid4()
        self.inventory = inventory
        self.playbook = playbook
        self.project_dir = project_dir
        if not callback:
            callback = DefaultCallback()
        self.cb = callback
        self.isolate = True
        self.envs = {}
        if extra_vars is None:
            extra_vars = {}
        self.extra_vars = extra_vars

    def copy_playbook(self):
        entry = os.path.basename(self.playbook)
        playbook_dir = os.path.dirname(self.playbook)
        project_playbook_dir = os.path.join(self.project_dir, "project")
        shutil.copytree(playbook_dir, project_playbook_dir, dirs_exist_ok=True)
        self.playbook = entry

    @property
    def playbook_project_dir(self):
        return os.path.join(self.project_dir, 'project')

    def run(self, verbosity=0, **kwargs):
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir, mode=0o755)
        self.copy_playbook()

        verbosity = get_ansible_log_verbosity(verbosity)
        private_env = safe_join(self.project_dir, 'env')
        if os.path.exists(private_env):
            shutil.rmtree(private_env)

        prepare_isolated_ansible_cfg(self.project_dir)

        kwargs = dict(kwargs)
        if use_ansible_docker_isolation():
            kwargs.update(docker_isolation_kwargs())
        elif self.isolate and not is_macos():
            kwargs['process_isolation'] = True
            kwargs['process_isolation_executable'] = 'bwrap'

        interface.run(
            private_data_dir=self.project_dir,
            inventory=self.inventory,
            playbook=self.playbook,
            verbosity=verbosity,
            event_handler=self.cb.event_handler,
            status_handler=self.cb.status_handler,
            # Docker EE workdir must be the staged playbook dir (not private_data_dir root).
            host_cwd=self.playbook_project_dir,
            envvars=self.envs,
            extravars=self.extra_vars,
            **kwargs
        )
        return self.cb


class SuperPlaybookRunner(PlaybookRunner):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.envs = {"ANSIBLE_SUPER_MODE": "1"}
        self.isolate = False


class UploadFileRunner:
    UPLOAD_STAGING_DIR = 'upload'

    def __init__(self, inventory, project_dir, job_id, dest_path, callback=None):
        self.id = uuid.uuid4()
        self.inventory = inventory
        self.project_dir = project_dir
        self.cb = DefaultCallback()
        upload_file_dir = safe_join(settings.SHARE_DIR, 'job_upload_file')
        self.share_src_dir = safe_join(upload_file_dir, str(job_id))
        self.dest_path = safe_join("/tmp", dest_path)

    def stage_upload_files(self):
        """Copy uploads into private_data_dir so Docker EE can read src for copy."""
        if not os.path.isdir(self.share_src_dir):
            raise FileNotFoundError(f'Upload source directory not found: {self.share_src_dir}')
        staged_dir = os.path.join(self.project_dir, self.UPLOAD_STAGING_DIR)
        if os.path.exists(staged_dir):
            shutil.rmtree(staged_dir)
        shutil.copytree(self.share_src_dir, staged_dir)
        return staged_dir

    def run(self, verbosity=0, **kwargs):
        if not os.path.exists(self.project_dir):
            os.makedirs(self.project_dir, mode=0o755)

        prepare_isolated_ansible_cfg(self.project_dir)
        src_path = self.stage_upload_files()

        verbosity = get_ansible_log_verbosity(verbosity)
        run_kwargs = {
            'private_data_dir': self.project_dir,
            'host_pattern': "*",
            'inventory': self.inventory,
            'module': 'copy',
            'module_args': f"src={src_path}/ dest={self.dest_path}/",
            'verbosity': verbosity,
            'event_handler': self.cb.event_handler,
            'status_handler': self.cb.status_handler,
            'host_cwd': self.project_dir,
            **kwargs,
        }
        if use_ansible_docker_isolation():
            run_kwargs.update(docker_isolation_kwargs())

        interface.run(**run_kwargs)
        try:
            shutil.rmtree(self.share_src_dir)
        except OSError as e:
            print(f"del upload tmp dir {self.share_src_dir} failed! {e}")
        return self.cb
