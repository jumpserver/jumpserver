import abc
from ..models import Account


class BaseBackends(object):

    def __init__(self, **kwargs):
        pass

    @abc.abstractmethod
    def create_secret(self, account: Account, secret: str):
        pass

    @abc.abstractmethod
    def read_secret(self, account: Account):
        pass

    @abc.abstractmethod
    def update_secret(self, account: Account, secret: str):
        pass

    @abc.abstractmethod
    def delete_secret(self, account: Account):
        pass
