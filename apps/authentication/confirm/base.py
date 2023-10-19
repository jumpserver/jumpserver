import abc


class BaseConfirm(abc.ABC):
    def __init__(self, user, request):
        self.user = user
        self.request = request

    @property
    @abc.abstractmethod
    def name(self) -> str:
        return ''

    @property
    @abc.abstractmethod
    def display_name(self) -> str:
        return ''

    @abc.abstractmethod
    def check(self) -> bool:
        return False

    @property
    def content(self):
        return []

    @abc.abstractmethod
    def authenticate(self, secret_key, mfa_type) -> tuple:
        return False, 'Error msg'
