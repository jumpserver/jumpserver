from abc import ABCMeta, abstractmethod


class Backend(metaclass=ABCMeta):
    @abstractmethod
    def get_metadata(self, account):
        pass

    @abstractmethod
    def get_secret(self, account):
        pass

    @abstractmethod
    def create_secret(self, account):
        pass

    @abstractmethod
    def update_secret(self, account):
        pass

    @abstractmethod
    def delete_secret(self, account):
        pass
