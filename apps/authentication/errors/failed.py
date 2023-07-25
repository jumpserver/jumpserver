# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from users.utils import LoginBlockUtil, MFABlockUtils, LoginIpBlockUtil
from . import const
from ..signals import post_auth_failed


class AuthFailedNeedLogMixin:
    username = ''
    request = None
    error = ''
    msg = ''

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        post_auth_failed.send(
            sender=self.__class__, username=self.username,
            request=self.request, reason=self.msg
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


class BlockGlobalIpLoginError(AuthFailedError):
    error = 'block_global_ip_login'

    def __init__(self, username, ip, **kwargs):
        if not self.msg:
            self.msg = const.block_ip_login_msg.format(settings.SECURITY_LOGIN_IP_LIMIT_TIME)
        LoginIpBlockUtil(ip).set_block_if_need()
        super().__init__(username=username, ip=ip, **kwargs)


class CredentialError(
    AuthFailedNeedLogMixin, AuthFailedNeedBlockMixin,
    BlockGlobalIpLoginError, AuthFailedError
):
    def __init__(self, error, username, ip, request):
        util = LoginBlockUtil(username, ip)
        times_remainder = util.get_remainder_times()
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME
        if times_remainder < 1:
            self.msg = const.block_user_login_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        else:
            default_msg = const.invalid_login_msg.format(
                times_try=times_remainder, block_time=block_time
            )
            if error == const.reason_password_failed:
                self.msg = default_msg
            else:
                self.msg = const.reason_choices.get(error, default_msg)
        # 先处理 msg 在 super，记录日志时原因才准确
        super().__init__(error=error, username=username, ip=ip, request=request)


class MFAFailedError(AuthFailedNeedLogMixin, AuthFailedError):
    error = const.reason_mfa_failed
    msg: str

    def __init__(self, username, request, ip, mfa_type, error):
        util = MFABlockUtils(username, ip)
        times_remainder = util.incr_failed_count()
        block_time = settings.SECURITY_LOGIN_LIMIT_TIME

        if times_remainder:
            self.msg = const.mfa_error_msg.format(
                error=error, times_try=times_remainder, block_time=block_time
            )
        else:
            self.msg = const.block_mfa_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, request=request)


class BlockMFAError(AuthFailedNeedLogMixin, AuthFailedError):
    error = 'block_mfa'

    def __init__(self, username, request, ip):
        self.msg = const.block_mfa_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, request=request, ip=ip)


class BlockLoginError(AuthFailedNeedBlockMixin, AuthFailedError):
    error = 'block_login'

    def __init__(self, username, ip):
        self.msg = const.block_user_login_msg.format(settings.SECURITY_LOGIN_LIMIT_TIME)
        super().__init__(username=username, ip=ip)


class SessionEmptyError(AuthFailedError):
    msg = const.session_empty_msg
    error = 'session_empty'


class ACLError(AuthFailedNeedLogMixin, AuthFailedError):
    msg = const.reason_acl_not_allow
    error = 'acl_error'

    def __init__(self, msg, **kwargs):
        self.msg = msg
        super().__init__(**kwargs)

    def as_data(self):
        return {
            "error": const.reason_acl_not_allow,
            "msg": self.msg
        }


class LoginACLIPAndTimePeriodNotAllowed(ACLError):
    def __init__(self, username, request, **kwargs):
        self.username = username
        self.request = request
        super().__init__(_("Current IP and Time period is not allowed"), **kwargs)


class MFACodeRequiredError(AuthFailedError):
    error = 'mfa_code_required'
    msg = _("Please enter MFA code")


class SMSCodeRequiredError(AuthFailedError):
    error = 'sms_code_required'
    msg = _("Please enter SMS code")


class UserPhoneNotSet(AuthFailedError):
    error = 'phone_not_set'
    msg = _('Phone not set')
