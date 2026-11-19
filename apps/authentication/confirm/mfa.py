from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

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
        if not mfa_type:
            raise ValidationError({'mfa_type': _("This field is required for MFA confirmation.")})
        mfa_backend = self.user.get_active_mfa_backend_by_type(mfa_type)
        if mfa_backend is None:
            raise ValidationError({'mfa_type': _('This verification method is not available.')})
        if mfa_backend.has_code and not secret_key:
            raise ValidationError({'secret_key': _("This field is required for code-based MFA confirmation.")})
        mfa_backend.set_request(self.request)
        ok, msg = mfa_backend.check_code(secret_key)
        return ok, msg
