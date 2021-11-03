from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from .base import BaseMFA
from ..backends.radius import RadiusBackend


class MFARadius(BaseMFA):
    name = 'otp_radius'
    display_name = _('OTP Radius')

    def check_code(self, code):
        backend = RadiusBackend()
        username = self.user.username
        user = backend.authenticate(
            None, username=username, password=code
        )
        return user is not None

    def has_set(self):
        return True

    def enabled(self):
        return settings.OTP_IN_RADIUS

