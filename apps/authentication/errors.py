# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.conf import settings

from .signals import post_auth_failed
from users.utils import (
    increase_login_failed_count, get_login_failed_count
)

reason_password_failed = 'password_failed'
reason_mfa_failed = 'mfa_failed'
reason_user_not_exist = 'user_not_exist'
reason_password_expired = 'password_expired'
reason_user_invalid = 'user_invalid'
reason_user_inactive = 'user_inactive'

reason_choices = {
    reason_password_failed: _('Username/password check failed'),
    reason_mfa_failed: _('MFA authentication failed'),
    reason_user_not_exist: _("Username does not exist"),
    reason_password_expired: _("Password expired"),
    reason_user_invalid: _('Disabled or expired'),
    reason_user_inactive: _("This account is inactive.")
}
old_reason_choices = {
    '0': '-',
    '1': reason_choices[reason_password_failed],
    '2': reason_choices[reason_mfa_failed],
    '3': reason_choices[reason_user_not_exist],
    '4': reason_choices[reason_password_expired],
}

session_empty_msg = _("No session found, check your cookie")
invalid_login_msg = _(
    "The username or password you entered is incorrect, "
    "please enter it again. "
    "You can also try {times_try} times "
    "(The account will be temporarily locked for {block_time} minutes)"
)
block_login_msg = _(
    "The account has been locked "
    "(please contact admin to unlock it or try again after {} minutes)"
)
mfa_failed_msg = _("MFA code invalid, or ntp sync server time")

mfa_required_msg = _("MFA required")
login_confirm_required_msg = _("Login confirm required")
login_confirm_wait_msg = _("Wait login confirm order for accept")
login_confirm_rejected_msg = _("Login confirm order was rejected")
login_confirm_order_not_found_msg = _("Order not found")


class AuthFailedNeedLogMixin:
    username = ''
    request = None
    error = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        post_auth_failed.send(
            sender=self.__class__, username=self.username,
            request=self.request, reason=self.error
        )


class AuthFailedNeedBlockMixin:
    username = ''
    ip = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        increase_login_failed_count(self.username, self.ip)


class AuthFailedError(Exception):
    username = ''
    msg = ''
    error = ''
    request = None
    ip = ''

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_data(self):
        return {
            'error': self.error,
            'msg': self.msg,
        }


class CredentialError(AuthFailedNeedLogMixin, AuthFailedNeedBlockMixin, AuthFailedError):
    def __init__(self, error, username, ip, request):
        super().__init__(error=error, username=username, ip=ip, request=request)
        times_up = settings.SECURITY_LOGIN_LIMIT_COUNT
        times_failed = get_login_failed_count(username, ip)
        times_try = int(times_up) - int(times_failed)
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME

        default_msg = invalid_login_msg.format(
            times_try=times_try, block_time=block_time
        )
        if error == reason_password_failed:
            self.msg = default_msg
        else:
            self.msg = reason_choices.get(error, default_msg)


class MFAFailedError(AuthFailedNeedLogMixin, AuthFailedError):
    reason = reason_mfa_failed
    error = 'mfa_failed'
    msg = mfa_failed_msg

    def __init__(self, username, request):
        super().__init__(username=username, request=request)


class BlockLoginError(AuthFailedNeedBlockMixin, AuthFailedError):
    error = 'block_login'
    msg = block_login_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)

    def __init__(self, username, ip):
        super().__init__(username=username, ip=ip)


class SessionEmptyError(AuthFailedError):
    msg = session_empty_msg
    error = 'session_empty_msg'


class MFARequiredError(AuthFailedError):
    msg = mfa_required_msg
    error = 'mfa_required_msg'

    def as_data(self):
        return {
            'error': self.error,
            'msg': self.msg,
            'choices': ['otp'],
            'url': reverse('api-auth:mfa-challenge')
        }


class LoginConfirmRequiredError(AuthFailedError):
    msg = login_confirm_required_msg
    error = 'login_confirm_required_msg'


class LoginConfirmError(AuthFailedError):
    msg = login_confirm_wait_msg
    error = 'login_confirm_wait_msg'

    def __init__(self, order_id, **kwargs):
        self.order_id = order_id
        super().__init__(**kwargs)

    def as_data(self):
        return {
            "error": self.error,
            "msg": self.msg,
            "order_id": self.order_id
        }


class LoginConfirmWaitError(LoginConfirmError):
    msg = login_confirm_wait_msg
    error = 'login_confirm_wait_msg'


class LoginConfirmRejectedError(LoginConfirmError):
    msg = login_confirm_rejected_msg
    error = 'login_confirm_rejected_msg'


class LoginConfirmOrderNotFound(LoginConfirmError):
    msg = login_confirm_order_not_found_msg
    error = 'login_confirm_order_not_found_msg'
