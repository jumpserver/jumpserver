from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .base import BaseMFA
from ..backends.radius import RadiusBackend

mfa_failed_msg = _("Radius verify code invalid")


class MFARadius(BaseMFA):
    name = 'otp_radius'
    display_name = _('Radius MFA')

    def check_code(self, code):
        backend = RadiusBackend()
        username = self.user.username
        user = backend.authenticate(
            None, username=username, password=code
        )
        ok = user is not None
        msg = '' if ok else mfa_failed_msg
        return ok, msg

    def has_set(self):
        return True

    @staticmethod
    def enabled():
        return settings.OTP_IN_RADIUS

    def get_set_url(self) -> str:
        return ''

    def can_unset(self):
        return False

    def unset(self):
        return ''

    @staticmethod
    def help_text_of_unset():
        return _("Radius global enabled, cannot disable")
        # return 'Radius 是全局的配置，不可以禁用'

    def get_unset_url(self) -> str:
        return ''
