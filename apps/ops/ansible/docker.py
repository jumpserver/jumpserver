import os
import shutil

from django.conf import settings

from .execution import get_ansible_execution_backend, use_ansible_ssh_executor

ANSIBLE_EE_IMAGE = 'jumpserver/ansible-executor-ssh:latest'

__all__ = [
    'ANSIBLE_EE_IMAGE',
    'docker_extravars',
    'prepare_isolated_ansible_cfg',
    'prepare_isolated_ansible_runtime',
    'stage_inventory_for_docker',
]


def docker_extravars(extra_vars):
    extravars = dict(extra_vars or {})
    if use_ansible_ssh_executor():
        extravars.setdefault('local_python_interpreter', '/usr/bin/python3')
    return extravars


def prepare_isolated_ansible_cfg(project_dir):
    if get_ansible_execution_backend() == 'native':
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
    if get_ansible_execution_backend() == 'native':
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
    if get_ansible_execution_backend() == 'native':
        return inventory_path
    standard_dir = os.path.join(project_dir, 'inventory')
    standard_path = os.path.join(standard_dir, 'hosts')
    if os.path.realpath(inventory_path) == os.path.realpath(standard_path):
        return standard_path
    os.makedirs(standard_dir, mode=0o700, exist_ok=True)
    shutil.copy2(inventory_path, standard_path)
    return standard_path
