from django.conf import settings
from django.utils.translation import gettext_lazy as _

from .base import BaseMFA
from ..backends.radius import RadiusBackend
from ..const import MFAType


class MFARadiusPush(BaseMFA):
    name = MFAType.RadiusPush.value
    display_name = MFAType.RadiusPush.label
    has_code = False
    web_login_only = True
    skip_cache_check = True

    @staticmethod
    def global_enabled():
        return settings.AUTH_RADIUS and settings.RADIUS_PUSH_ENABLED

    def is_active(self):
        return self.global_enabled()

    def _check_code(self, code):
        return False, _('Use Send push to verify your sign-in.')

    @classmethod
    def for_user(cls, user):
        if user and user.is_valid and user.mfa_enabled and cls.global_enabled():
            return user.get_active_mfa_backend_by_type(cls.name)
        return None

    @classmethod
    def login_attempt(cls, request, user):
        from ..services.radius_push import RadiusPushAttempt

        if cls.for_user(user):
            return RadiusPushAttempt.for_session(request.session, user)
        return None

    def send_push(self, timeout):
        return RadiusBackend().authenticate_push(self.user.username, settings.RADIUS_PUSH_TRIGGER, timeout)

    def get_enable_url(self):
        return ''

    def get_disable_url(self):
        return ''

    def can_disable(self):
        return False

    def disable(self):
        return ''
