__all__ = ['CommandInBlackListException', 'AnsibleDockerImageNotFound']


class CommandInBlackListException(Exception):
    pass


class AnsibleDockerImageNotFound(Exception):
    """Retained for rotation results that failed before remote execution started."""

    pass
