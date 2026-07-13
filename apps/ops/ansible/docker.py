import os
import shutil

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.utils.safe import safe_run_cmd
from .exception import AnsibleDockerImageNotFound

ANSIBLE_EE_IMAGE = 'jumpserver/ansible-executor:latest'
ANSIBLE_EE_PYTHON_INTERPRETER = '/usr/bin/python3.11'

__all__ = [
    'ANSIBLE_EE_IMAGE',
    'ANSIBLE_EE_PYTHON_INTERPRETER',
    'use_ansible_docker_isolation',
    'docker_extravars',
    'docker_isolation_kwargs',
    'prepare_isolated_ansible_cfg',
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
    result = safe_run_cmd(['docker', 'image', 'inspect', ANSIBLE_EE_IMAGE])
    if not result or result.returncode != 0:
        raise AnsibleDockerImageNotFound(
            _('Ansible Docker image "%(image)s" not found. '
              'You can disable this option in System Settings - Feature Settings - Job Center - '
              'Ansible Docker isolation to run locally. '
              'Please run: docker pull %(image)s')
            % {'image': ANSIBLE_EE_IMAGE}
        )
