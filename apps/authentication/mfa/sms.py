from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .base import BaseMFA
from common.sdk.sms import SendAndVerifySMSUtil


sms_failed_msg = _("SMS verify code invalid")


class MFASms(BaseMFA):
    name = 'sms'
    display_name = _("SMS")

    def __init__(self, user):
        super().__init__(user)
        self.sms = SendAndVerifySMSUtil(user.phone)

    def check_code(self, code):
        ok = self.sms.verify(code)
        msg = '' if ok else sms_failed_msg
        return ok, msg

    def has_set(self):
        return self.user.phone

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        self.sms.gen_and_send()

    @staticmethod
    def enabled():
        return settings.SMS_ENABLED
