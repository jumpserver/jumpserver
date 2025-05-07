from django.conf import settings
from django.utils.translation import gettext_lazy as _

from authentication.mfa.base import BaseMFA
from ..const import MFAType


class MFAPasskey(BaseMFA):
    name = MFAType.Passkey.value
    display_name = MFAType.Passkey.name
    placeholder = 'Passkey'
    has_code = False

    def _check_code(self, code):
        assert self.is_authenticated()

        return False, ''

    def is_active(self):
        if not self.is_authenticated():
            return True
        return self.user.passkey_set.count()

    @staticmethod
    def global_enabled():
        return settings.AUTH_PASSKEY

    def get_enable_url(self) -> str:
        return '/ui/#/profile/index'

    def get_disable_url(self) -> str:
        return '/ui/#/profile/index'

    def disable(self):
        assert self.is_authenticated()
        self.user.face_vector = None
        self.user.save(update_fields=['face_vector'])

    def can_disable(self) -> bool:
        return False

    @staticmethod
    def help_text_of_enable():
        return _("Bind face to enable")

    @staticmethod
    def help_text_of_disable():
        return _("Unbind face to disable")
