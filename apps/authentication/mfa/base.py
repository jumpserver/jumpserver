import abc

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _


class BaseMFA(abc.ABC):
    placeholder = _('Please input security code')
    skip_cache_check = False
    has_code = True

    def __init__(self, user):
        """
        :param user:  Authenticated user, Anonymous or None
        因为首页登录时，可能没法获取到一些状态
        """
        self.user = user
        self.request = None

    def check_code(self, code):
        if self.skip_cache_check:
            return self._check_code(code)

        cache_key = f'{self.name}_{self.user.username}'
        cache_code = cache.get(cache_key)
        if cache_code == code:
            return False, _(
                "The two-factor code you entered has either already been used or has expired. "
                "Please request a new one."
            )

        ok, msg = self._check_code(code)
        if not ok:
            return False, msg

        cache.set(cache_key, code, 60 * 5)
        return True, msg

    def is_authenticated(self):
        return self.user and self.user.is_authenticated

    def set_request(self, request):
        self.request = request

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
    def _check_code(self, code) -> tuple:
        return False, 'Error msg'

    @abc.abstractmethod
    def is_active(self):
        return False

    @staticmethod
    @abc.abstractmethod
    def global_enabled():
        return False

    @abc.abstractmethod
    def get_enable_url(self) -> str:
        return ''

    @abc.abstractmethod
    def get_disable_url(self) -> str:
        return ''

    @abc.abstractmethod
    def disable(self):
        pass

    @abc.abstractmethod
    def can_disable(self) -> bool:
        return True

    @staticmethod
    def help_text_of_enable():
        return ''

    @staticmethod
    def help_text_of_disable():
        return ''
