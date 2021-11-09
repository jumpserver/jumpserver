import abc
from .client import VaultClient


class BaseVault(abc.ABC):

    def __init__(self, client: VaultClient):
        self.client = client.client

    @abc.abstractmethod
    def enable_secrets_engine(self) -> None:
        pass
