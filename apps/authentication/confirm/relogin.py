from math import isfinite

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .base import BaseConfirm
from ..const import ConfirmType

SPECIFIED_TIME = 5

RELOGIN_ERROR = _('Login time has exceeded {} minutes, please login again').format(SPECIFIED_TIME)


class ConfirmReLogin(BaseConfirm):
    name = ConfirmType.RELOGIN.value
    display_name = ConfirmType.RELOGIN.name

    def check(self):
        return not self.user.is_password_authenticate()

    @property
    def login_timestamp(self):
        # login_time is an audit value that a repeated login-guard visit can refresh.
        # Only the Session's original authentication time can prove a recent login.
        policy = getattr(self.request.session, 'login_policy', None) or {}
        value = policy.get('authenticated_at')
        if type(value) not in (int, float) or not isfinite(value):
            return None
        return value

    def authenticate(self, secret_key, mfa_type):
        login_timestamp = self.login_timestamp
        if login_timestamp is None:
            return False, RELOGIN_ERROR
        elapsed = timezone.now().timestamp() - login_timestamp
        if not 0 <= elapsed < SPECIFIED_TIME * 60:
            return False, RELOGIN_ERROR
        return True, ''
