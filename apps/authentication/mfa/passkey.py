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
        return '/ui/#/profile/passkeys'

    def get_disable_url(self) -> str:
        return '/ui/#/profile/passkeys'

    def disable(self):
        pass

    def can_disable(self) -> bool:
        return False

    @staticmethod
    def help_text_of_enable():
        return _("Using passkey as MFA")

    @staticmethod
    def help_text_of_disable():
        return _("Using passkey as MFA")
