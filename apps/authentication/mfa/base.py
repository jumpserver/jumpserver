import abc


class BaseMFA(abc.ABC):
    def __init__(self, user):
        self.user = user

    @property
    @abc.abstractmethod
    def name(self):
        return ''

    @property
    @abc.abstractmethod
    def display_name(self):
        return ''

    @staticmethod
    def challenge_required():
        return False

    def send_challenge(self):
        pass

    @abc.abstractmethod
    def check_code(self, code) -> tuple:
        return False, 'Error msg'

    @abc.abstractmethod
    def has_set(self):
        return False

    @staticmethod
    @abc.abstractmethod
    def enabled():
        return False
