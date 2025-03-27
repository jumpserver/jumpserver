from users.models import User

from .base import BaseConfirm
from ..const import ConfirmType


class ConfirmMFA(BaseConfirm):
    name = ConfirmType.MFA.value
    display_name = ConfirmType.MFA.name

    def check(self):
        return self.user.active_mfa_backends and self.user.mfa_enabled

    @property
    def content(self):
        backends = User.get_user_mfa_backends(self.user)
        return [{
            'name': backend.name,
            'disabled': not bool(backend.is_active()),
            'display_name': backend.display_name,
            'placeholder': backend.placeholder,
        } for backend in backends]

    def authenticate(self, secret_key, mfa_type):
        mfa_backend = self.user.get_mfa_backend_by_type(mfa_type)
        mfa_backend.set_request(self.request)
        ok, msg = mfa_backend.check_code(secret_key)
        return ok, msg
