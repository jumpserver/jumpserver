from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from common.utils import random_string
from common.utils.verify_code import SendAndVerifyCodeUtil
from settings.utils import get_login_title
from .base import BaseMFA

email_failed_msg = _("Email verify code invalid")


class MFAEmail(BaseMFA):
    name = 'email'
    display_name = _('Email')
    placeholder = _('Email verification code')

    def _check_code(self, code):
        assert self.is_authenticated()
        sender_util = SendAndVerifyCodeUtil(self.user.email, backend=self.name)
        ok = sender_util.verify(code)
        msg = '' if ok else email_failed_msg
        return ok, msg

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.email

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        code = random_string(settings.SMS_CODE_LENGTH, lower=False, upper=False)
        subject = '%s: %s' % (get_login_title(), _('MFA code'))
        context = {
            'user': self.user, 'title': subject, 'code': code,
        }
        message = render_to_string('authentication/_msg_mfa_email_code.html', context)
        content = {'subject': subject, 'message': message}
        sender_util = SendAndVerifyCodeUtil(
            self.user.email, code=code, backend=self.name, timeout=60, **content
        )
        sender_util.gen_and_send_async()

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
