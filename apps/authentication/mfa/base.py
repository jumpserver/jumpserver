import abc

from django.utils.translation import ugettext_lazy as _


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

    @property
    def placeholder(self):
        return _('Please input security code')

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

    @abc.abstractmethod
    def get_set_url(self) -> str:
        return ''

    @abc.abstractmethod
    def get_unset_url(self) -> str:
        return ''

    @abc.abstractmethod
    def unset(self):
        pass

    @abc.abstractmethod
    def can_unset(self) -> bool:
        return True

    @staticmethod
    def help_text_of_set():
        return ''

    @staticmethod
    def help_text_of_unset():
        return ''

