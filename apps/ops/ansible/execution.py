from django.conf import settings


def get_ansible_execution_backend():
    backend = getattr(settings, 'ANSIBLE_EXECUTION_BACKEND', '')
    if not backend:
        return 'docker' if settings.ANSIBLE_DOCKER_ENABLED else 'native'
    if backend not in ('native', 'docker', 'ssh'):
        raise ValueError('ANSIBLE_EXECUTION_BACKEND must be native, docker or ssh')
    return backend


def use_ansible_ssh_executor():
    return get_ansible_execution_backend() == 'ssh'
