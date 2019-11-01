# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _

password_failed = _('Username/password check failed')
mfa_failed = _('MFA authentication failed')
user_not_exist = _("Username does not exist")
password_expired = _("Password expired")
user_invalid = _('Disabled or expired')
ip_blocked = _("Log in frequently and try again later")

mfa_required = _("MFA required")
login_confirm_required = _("Login confirm required")
login_confirm_wait = _("Wait login confirm")


class AuthFailedError(Exception):
    def __init__(self, reason, error=None, username=None):
        self.reason = reason
        self.error = error
        self.username = username


class MFARequiredError(Exception):
    reason = mfa_required
    error = 'mfa_required'


class LoginConfirmRequiredError(Exception):
    reason = login_confirm_required
    error = 'login_confirm_required'


class LoginConfirmWaitError(Exception):
    reason = login_confirm_wait
    error = 'login_confirm_wait'


class LoginConfirmRejectedError(Exception):
    reason = login_confirm_wait
    error = 'login_confirm_rejected'
