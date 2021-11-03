from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .base import BaseMFA
from common.sdk.sms import SendAndVerifySMSUtil


class MFASms(BaseMFA):
    name = 'sms'
    display_name = _("SMS")

    def __init__(self, user):
        super().__init__(user)
        self.sms = SendAndVerifySMSUtil(user.phone)

    def check_code(self, code):
        return self.sms.verify(code)

    def has_set(self):
        return self.user.phone

    @staticmethod
    def challenge_required():
        return True

    def send_challenge(self):
        self.sms.gen_and_send()

    def enabled(self):
        return settings.SMS_ENABLED
