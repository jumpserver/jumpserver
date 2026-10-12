from users.models import User
from users.utils import MFABlockUtils
from common.utils import get_request_ip
from django.utils.translation import gettext_lazy as _

from .base import BaseConfirm
from ..const import ConfirmType
from ..errors.const import block_mfa_msg


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
        util = MFABlockUtils(self.user.username, get_request_ip(self.request))
        if util.is_block():
            return False, block_mfa_msg.format(util.key_ttl // 60)
        mfa_backend = self.user.get_active_mfa_backend_by_type(mfa_type)
        if mfa_backend is None:
            util.incr_failed_count()
            return False, _('The MFA type ({}) is not enabled').format(mfa_type)
        mfa_backend.set_request(self.request)
        ok, msg = mfa_backend.check_code(secret_key)
        if ok:
            util.clean_failed_count()
        elif util.incr_failed_count() <= 0:
            msg = block_mfa_msg.format(util.key_ttl // 60)
        return ok, msg
