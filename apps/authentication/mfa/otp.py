from django.utils.translation import gettext_lazy as _

from .base import BaseMFA


class MFAOtp(BaseMFA):
    name = 'otp'
    display_name = _('One-time password')

    def check_code(self, code):
        from users.utils import check_otp_code
        return check_otp_code(self.user.otp_secret_key, code)

    def has_set(self):
        return self.user.otp_secret_key

    def enabled(self):
        return True



