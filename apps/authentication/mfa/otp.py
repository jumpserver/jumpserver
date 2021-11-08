from django.utils.translation import gettext_lazy as _
from django.shortcuts import reverse

from .base import BaseMFA


otp_failed_msg = _("One-time password invalid, or ntp sync server time")


class MFAOtp(BaseMFA):
    name = 'otp'
    display_name = 'MFA'

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

    def get_set_url(self) -> str:
        return reverse('authentication:user-otp-enable-start')

    def unset(self):
        self.user.otp_secret_key = ''
        self.user.save(update_fields=['otp_secret_key'])

    def can_unset(self) -> bool:
        return True

    def get_unset_url(self):
        return reverse('authentication:user-otp-disable')

    @staticmethod
    def help_text_of_set():
        return _("Download MFA APP, Using dynamic code")
        # return '下载安装 APP，使用动态码验证'

    def help_text_of_unset(self):
        return ''

