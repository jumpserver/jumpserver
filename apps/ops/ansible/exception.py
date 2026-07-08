__all__ = ['CommandInBlackListException', 'AnsibleDockerImageNotFound']


class CommandInBlackListException(Exception):
    pass


class AnsibleDockerImageNotFound(Exception):
    pass
