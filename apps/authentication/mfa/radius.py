from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .base import BaseMFA
from ..backends.radius import RadiusBackend

mfa_failed_msg = _("Radius verify code invalid")


class MFARadius(BaseMFA):
    name = 'otp_radius'
    display_name = 'Radius'
    placeholder = _("Radius verification code")

    def check_code(self, code):
        assert self.is_authenticated()
        backend = RadiusBackend()
        username = self.user.username
        user = backend.authenticate(
            None, username=username, password=code
        )
        ok = user is not None
        msg = '' if ok else mfa_failed_msg
        return ok, msg

    def is_active(self):
        return True

    @staticmethod
    def global_enabled():
        return settings.OTP_IN_RADIUS

    def get_enable_url(self) -> str:
        return ''

    def can_disable(self):
        return False

    def disable(self):
        return ''

    @staticmethod
    def help_text_of_disable():
        return _("Radius global enabled, cannot disable")

    def get_disable_url(self) -> str:
        return ''
