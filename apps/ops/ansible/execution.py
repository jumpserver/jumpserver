from django.conf import settings


def get_ansible_execution_backend():
    return 'ssh' if settings.ANSIBLE_DOCKER_ENABLED else 'native'


def use_ansible_ssh_executor():
    return get_ansible_execution_backend() == 'ssh'
