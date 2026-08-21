import os
import shutil

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.utils.safe import safe_run_cmd
from .exception import AnsibleDockerImageNotFound

ANSIBLE_EE_IMAGE = 'jumpserver/ansible-executor:latest'
ANSIBLE_EE_PYTHON_INTERPRETER = '/usr/bin/python3.14'

__all__ = [
    'ANSIBLE_EE_IMAGE',
    'ANSIBLE_EE_PYTHON_INTERPRETER',
    'use_ansible_docker_isolation',
    'docker_extravars',
    'docker_isolation_kwargs',
    'prepare_isolated_ansible_cfg',
    'prepare_isolated_ansible_runtime',
    'stage_inventory_for_docker',
    'ensure_ansible_docker_image',
]


def use_ansible_docker_isolation():
    return settings.ANSIBLE_DOCKER_ENABLED


def docker_extravars(extra_vars):
    extravars = dict(extra_vars or {})
    if use_ansible_docker_isolation():
        extravars.setdefault('local_python_interpreter', ANSIBLE_EE_PYTHON_INTERPRETER)
    return extravars


def docker_isolation_kwargs(project_dir):
    return {
        'process_isolation': True,
        'process_isolation_executable': 'docker',
        'container_image': ANSIBLE_EE_IMAGE,
        'container_options': ['--network=jms_net'],
        'container_volume_mounts': [f'{project_dir}:{project_dir}:Z'],
    }


def prepare_isolated_ansible_cfg(project_dir):
    if not use_ansible_docker_isolation():
        return
    src = os.path.join(settings.APPS_DIR, 'libs', 'ansible', 'ansible.cfg')
    dst = os.path.join(project_dir, 'ansible.cfg')
    shutil.copyfile(src, dst)


def prepare_isolated_ansible_runtime(project_dir):
    """Stage the app's Ansible plugins for the isolated execution image.

    The executor image supplies system packages and database drivers, but its
    embedded copy of JumpServer's custom modules can lag behind the running
    core image.  Always use the modules shipped with the current application
    so playbooks and module argument specs stay in sync.
    """
    if not use_ansible_docker_isolation():
        return {}

    prepare_isolated_ansible_cfg(project_dir)

    source_libs_dir = os.path.join(settings.APPS_DIR, 'libs')
    source_ansible_dir = os.path.join(source_libs_dir, 'ansible')
    runtime_apps_dir = os.path.join(project_dir, 'jms_runtime', 'apps')
    runtime_libs_dir = os.path.join(runtime_apps_dir, 'libs')
    runtime_ansible_dir = os.path.join(runtime_libs_dir, 'ansible')

    os.makedirs(runtime_libs_dir, mode=0o700, exist_ok=True)
    libs_init = os.path.join(source_libs_dir, '__init__.py')
    if os.path.isfile(libs_init):
        shutil.copy2(libs_init, runtime_libs_dir)
    shutil.copytree(
        source_ansible_dir,
        runtime_ansible_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.DS_Store'),
    )

    module_paths = [
        os.path.join(runtime_ansible_dir, 'modules'),
        os.path.join(project_dir, 'project', 'modules'),
        os.path.join(project_dir, 'modules'),
    ]

    return {
        'ANSIBLE_CONFIG': os.path.join(project_dir, 'ansible.cfg'),
        'ANSIBLE_LIBRARY': os.pathsep.join(module_paths),
        'PYTHONPATH': runtime_apps_dir,
    }


def stage_inventory_for_docker(project_dir, inventory_path):
    if not use_ansible_docker_isolation():
        return inventory_path
    standard_dir = os.path.join(project_dir, 'inventory')
    standard_path = os.path.join(standard_dir, 'hosts')
    if os.path.realpath(inventory_path) == os.path.realpath(standard_path):
        return standard_path
    os.makedirs(standard_dir, mode=0o700, exist_ok=True)
    shutil.copy2(inventory_path, standard_path)
    return standard_path


def ensure_ansible_docker_image():
    if not use_ansible_docker_isolation():
        return
    result = safe_run_cmd(['docker', 'image', 'inspect', ANSIBLE_EE_IMAGE], quiet=True)
    if not result or result.returncode != 0:
        raise AnsibleDockerImageNotFound(
            _('The Ansible Docker image "%(image)s" was not found. '
              'To run jobs locally instead, disable "Docker isolation for Ansible" under '
              'System Settings > Feature Settings > Job Center. '
              'To continue using the Docker execution environment, run this command on the '
              'Ansible worker: docker pull %(image)s')
            % {'image': ANSIBLE_EE_IMAGE}
        )
