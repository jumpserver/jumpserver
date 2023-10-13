from datetime import datetime

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .base import BaseConfirm

SPECIFIED_TIME = 5

RELOGIN_ERROR = _('Login time has exceeded {} minutes, please login again').format(SPECIFIED_TIME)


class ConfirmReLogin(BaseConfirm):
    name = 'relogin'
    display_name = 'Re-Login'

    def check(self):
        return not self.user.is_password_authenticate()

    def authenticate(self, secret_key, mfa_type):
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
        now = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
        login_time = self.request.session.get('login_time')
        msg = RELOGIN_ERROR
        if not login_time:
            return False, msg
        login_time = datetime.strptime(login_time, '%Y-%m-%d %H:%M:%S')
        if (now - login_time).seconds >= SPECIFIED_TIME * 60:
            return False, msg
        return True, ''
