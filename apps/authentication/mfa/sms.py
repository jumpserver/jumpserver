from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.utils.verify_code import SendAndVerifyCodeUtil
from .base import BaseMFA

sms_failed_msg = _("SMS verify code invalid")


class MFASms(BaseMFA):
    name = 'sms'
    display_name = _("SMS")
    placeholder = _("SMS verification code")

    def __init__(self, user):
        super().__init__(user)
        phone = user.phone if self.is_authenticated() else ''
        self.sms = SendAndVerifyCodeUtil(phone, backend=self.name)

    def check_code(self, code):
        assert self.is_authenticated()
        ok = False
        msg = ''
        try:
            ok = self.sms.verify(code)
        except Exception as e:
            msg = str(e)
        return ok, msg

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.phone

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        self.sms.gen_and_send_async()

    @staticmethod
    def global_enabled():
        return settings.SMS_ENABLED

    def get_enable_url(self) -> str:
        return '/ui/#/profile/setting?activeTab=ProfileUpdate'

    def can_disable(self) -> bool:
        return True

    def disable(self):
        return '/ui/#/profile/setting?activeTab=ProfileUpdate'

    @staticmethod
    def help_text_of_enable():
        return _("Set phone number to enable")

    @staticmethod
    def help_text_of_disable():
        return _("Clear phone number to disable")

    def get_disable_url(self) -> str:
        return '/ui/#/profile/setting?activeTab=ProfileUpdate'
