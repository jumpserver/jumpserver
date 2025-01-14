from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from common.utils import random_string
from common.utils.verify_code import SendAndVerifyCodeUtil
from settings.utils import get_login_title
from users.serializers import SmsUserSerializer
from .base import BaseMFA

otp_failed_msg = _("OTP code invalid, or server time error")


class MFAEmail(BaseMFA):
    name = 'email'
    display_name = _('Email')
    placeholder = _('OTP verification code')

    def __init__(self, user):
        super().__init__(user)
        self.email, self.user_info = '', None
        if self.is_authenticated():
            self.email = user.email
            self.user_info = SmsUserSerializer(user).data

    def check_code(self, code):
        assert self.is_authenticated()
        ok = False
        msg = ''
        try:
            ok = self.email.verify(code)
        except Exception as e:
            msg = str(e)
        return ok, msg

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.email

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        code = random_string(6, lower=False, upper=False)
        subject = '%s: %s' % (get_login_title(), _('Forgot password'))
        context = {
            'user': self.user, 'title': subject, 'code': code,
        }
        subject = '%s: %s' % (get_login_title(), _('Forgot password'))
        message = render_to_string('authentication/_msg_reset_password_code.html', context)
        content = {'subject': subject, 'message': message}
        self.email = SendAndVerifyCodeUtil(
            self.email, code=code, backend=self.name, user_info=self.user_info, **content
        )
        self.email.gen_and_send_async()

    @staticmethod
    def global_enabled():
        return settings.SECURITY_MFA_BY_EMAIL

    def disable(self):
        return '/ui/#/profile/index'

    def get_enable_url(self) -> str:
        return ''

    def can_disable(self) -> bool:
        return False

    def get_disable_url(self):
        return ''

    @staticmethod
    def help_text_of_enable():
        return ''

    def help_text_of_disable(self):
        return ''
