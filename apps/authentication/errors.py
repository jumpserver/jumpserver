# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.conf import settings

from common.exceptions import JMSException
from .signals import post_auth_failed
from users.utils import LoginBlockUtil, MFABlockUtils

reason_password_failed = 'password_failed'
reason_password_decrypt_failed = 'password_decrypt_failed'
reason_mfa_failed = 'mfa_failed'
reason_mfa_unset = 'mfa_unset'
reason_user_not_exist = 'user_not_exist'
reason_password_expired = 'password_expired'
reason_user_invalid = 'user_invalid'
reason_user_inactive = 'user_inactive'
reason_user_expired = 'user_expired'
reason_backend_not_match = 'backend_not_match'
reason_acl_not_allow = 'acl_not_allow'
only_local_users_are_allowed = 'only_local_users_are_allowed'

reason_choices = {
    reason_password_failed: _('Username/password check failed'),
    reason_password_decrypt_failed: _('Password decrypt failed'),
    reason_mfa_failed: _('MFA failed'),
    reason_mfa_unset: _('MFA unset'),
    reason_user_not_exist: _("Username does not exist"),
    reason_password_expired: _("Password expired"),
    reason_user_invalid: _('Disabled or expired'),
    reason_user_inactive: _("This account is inactive."),
    reason_user_expired: _("This account is expired"),
    reason_backend_not_match: _("Auth backend not match"),
    reason_acl_not_allow: _("ACL is not allowed"),
    only_local_users_are_allowed: _("Only local users are allowed")
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
block_mfa_msg = _(
    "The account has been locked "
    "(please contact admin to unlock it or try again after {} minutes)"
)
mfa_failed_msg = _(
    "MFA code invalid, or ntp sync server time, "
    "You can also try {times_try} times "
    "(The account will be temporarily locked for {block_time} minutes)"
)

mfa_required_msg = _("MFA required")
mfa_unset_msg = _("MFA not set, please set it first")
login_confirm_required_msg = _("Login confirm required")
login_confirm_wait_msg = _("Wait login confirm ticket for accept")
login_confirm_error_msg = _("Login confirm ticket was {}")


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
        LoginBlockUtil(self.username, self.ip).incr_failed_count()


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

    def __str__(self):
        return str(self.msg)


class CredentialError(AuthFailedNeedLogMixin, AuthFailedNeedBlockMixin, AuthFailedError):
    def __init__(self, error, username, ip, request):
        super().__init__(error=error, username=username, ip=ip, request=request)
        util = LoginBlockUtil(username, ip)
        times_remainder = util.get_remainder_times()
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME

        default_msg = invalid_login_msg.format(
            times_try=times_remainder, block_time=block_time
        )
        if error == reason_password_failed:
            self.msg = default_msg
        else:
            self.msg = reason_choices.get(error, default_msg)


class MFAFailedError(AuthFailedNeedLogMixin, AuthFailedError):
    error = reason_mfa_failed
    msg: str

    def __init__(self, username, request, ip):
        util = MFABlockUtils(username, ip)
        util.incr_failed_count()

        times_remainder = util.get_remainder_times()
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME

        if times_remainder:
            self.msg = mfa_failed_msg.format(
                times_try=times_remainder, block_time=block_time
            )
        else:
            self.msg = block_mfa_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, request=request)


class BlockMFAError(AuthFailedNeedLogMixin, AuthFailedError):
    error = 'block_mfa'

    def __init__(self, username, request, ip):
        self.msg = block_mfa_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, request=request, ip=ip)


class MFAUnsetError(AuthFailedNeedLogMixin, AuthFailedError):
    error = reason_mfa_unset
    msg = mfa_unset_msg

    def __init__(self, user, request, url):
        super().__init__(username=user.username, request=request)
        self.user = user
        self.url = url


class BlockLoginError(AuthFailedNeedBlockMixin, AuthFailedError):
    error = 'block_login'

    def __init__(self, username, ip):
        self.msg = block_login_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, ip=ip)


class SessionEmptyError(AuthFailedError):
    msg = session_empty_msg
    error = 'session_empty'


class NeedMoreInfoError(Exception):
    error = ''
    msg = ''

    def __init__(self, error='', msg=''):
        if error:
            self.error = error
        if msg:
            self.msg = msg

    def as_data(self):
        return {
            'error': self.error,
            'msg': self.msg,
        }


class MFARequiredError(NeedMoreInfoError):
    msg = mfa_required_msg
    error = 'mfa_required'

    def as_data(self):
        return {
            'error': self.error,
            'msg': self.msg,
            'data': {
                'choices': ['code'],
                'url': reverse('api-auth:mfa-challenge')
            }
        }


class ACLError(AuthFailedNeedLogMixin, AuthFailedError):
    msg = reason_acl_not_allow
    error = 'acl_error'

    def __init__(self, msg, **kwargs):
        self.msg = msg
        super().__init__(**kwargs)

    def as_data(self):
        return {
            "error": reason_acl_not_allow,
            "msg": self.msg
        }


class LoginIPNotAllowed(ACLError):
    def __init__(self, username, request, **kwargs):
        self.username = username
        self.request = request
        super().__init__(_("IP is not allowed"), **kwargs)


class LoginConfirmBaseError(NeedMoreInfoError):
    def __init__(self, ticket_id, **kwargs):
        self.ticket_id = ticket_id
        super().__init__(**kwargs)

    def as_data(self):
        return {
            "error": self.error,
            "msg": self.msg,
            "data": {
                "ticket_id": self.ticket_id
            }
        }


class LoginConfirmWaitError(LoginConfirmBaseError):
    msg = login_confirm_wait_msg
    error = 'login_confirm_wait'


class LoginConfirmOtherError(LoginConfirmBaseError):
    error = 'login_confirm_error'

    def __init__(self, ticket_id, status):
        msg = login_confirm_error_msg.format(status)
        super().__init__(ticket_id=ticket_id, msg=msg)


class SSOAuthClosed(JMSException):
    default_code = 'sso_auth_closed'
    default_detail = _('SSO auth closed')


class PasswdTooSimple(JMSException):
    default_code = 'passwd_too_simple'
    default_detail = _('Your password is too simple, please change it for security')

    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url


class PasswdNeedUpdate(JMSException):
    default_code = 'passwd_need_update'
    default_detail = _('You should to change your password before login')

    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url


class PasswordRequireResetError(JMSException):
    default_code = 'passwd_has_expired'
    default_detail = _('Your password has expired, please reset before logging in')

    def __init__(self, url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.url = url


class WeComCodeInvalid(JMSException):
    default_code = 'wecom_code_invalid'
    default_detail = 'Code invalid, can not get user info'


class WeComBindAlready(JMSException):
    default_code = 'wecom_bind_already'
    default_detail = 'WeCom already binded'


class WeComNotBound(JMSException):
    default_code = 'wecom_not_bound'
    default_detail = 'WeCom is not bound'


class DingTalkNotBound(JMSException):
    default_code = 'dingtalk_not_bound'
    default_detail = 'DingTalk is not bound'


class PasswdInvalid(JMSException):
    default_code = 'passwd_invalid'
    default_detail = _('Your password is invalid')
