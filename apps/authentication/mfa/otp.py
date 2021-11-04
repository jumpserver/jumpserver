from django.utils.translation import gettext_lazy as _

from .base import BaseMFA


otp_failed_msg = _("One-time password invalid, or ntp sync server time")


class MFAOtp(BaseMFA):
    name = 'otp'
    display_name = _('One-time password')

    def check_code(self, code):
        from users.utils import check_otp_code
        ok = check_otp_code(self.user.otp_secret_key, code)
        msg = '' if ok else otp_failed_msg
        return ok, msg

    def has_set(self):
        return self.user.otp_secret_key

    @staticmethod
    def enabled():
        return True



