from django.utils.translation import gettext_lazy as _

from authentication.mixins import authenticate
from .base import BaseConfirm
from ..const import ConfirmType


class ConfirmPassword(BaseConfirm):
    name = ConfirmType.PASSWORD.value
    display_name = ConfirmType.PASSWORD.name

    def check(self):
        return self.user.is_password_authenticate()

    def authenticate(self, secret_key, mfa_type):
        ok = authenticate(self.request, username=self.user.username, password=secret_key)
        msg = '' if ok else _('Authentication failed password incorrect')
        return ok, msg

    @property
    def content(self):
        return [
            {
                'name': 'password',
                'display_name': _('Password'),
                'disabled': False,
                'placeholder': _('Password'),
            }
        ]
