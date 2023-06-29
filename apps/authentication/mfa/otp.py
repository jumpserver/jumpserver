from django.utils.translation import gettext_lazy as _

from .base import BaseMFA


class MFAOtp(BaseMFA):
    name = 'otp'
    display_name = _('OTP')
    placeholder = _('OTP verification code')

    def check_code(self, code):
        from users.utils import check_otp_code
        assert self.is_authenticated()

        ok = check_otp_code(self.user.otp_secret_key, code)
        from authentication.const import OTP_FAILED_MSG
        msg = '' if ok else OTP_FAILED_MSG
        return ok, msg

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.otp_secret_key

    @staticmethod
    def global_enabled():
        return True

    def disable(self):
        assert self.is_authenticated()
        self.user.otp_secret_key = ''
        self.user.save(update_fields=['otp_secret_key'])

    def can_disable(self) -> bool:
        return True

    @staticmethod
    def help_text_of_enable():
        return _("Virtual OTP based MFA")

    def help_text_of_disable(self):
        return ''

