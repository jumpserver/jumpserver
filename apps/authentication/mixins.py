# -*- coding: utf-8 -*-
#
import time

from common.utils import get_object_or_none, get_request_ip, get_logger
from users.models import User
from users.utils import (
    is_block_login, clean_failed_count, increase_login_failed_count
)
from . import errors
from .utils import check_user_valid
from .signals import post_auth_success, post_auth_failed

logger = get_logger(__name__)


class AuthMixin:
    request = None

    def get_user_from_session(self):
        if self.request.session.is_empty():
            raise errors.SessionEmptyError()
        if self.request.user and not self.request.user.is_anonymous:
            return self.request.user
        user_id = self.request.session.get('user_id')
        if not user_id:
            user = None
        else:
            user = get_object_or_none(User, pk=user_id)
        if not user:
            raise errors.SessionEmptyError()
        return user

    def get_request_ip(self):
        ip = ''
        if hasattr(self.request, 'data'):
            ip = self.request.data.get('remote_addr', '')
        ip = ip or get_request_ip(self.request)
        return ip

    def check_is_block(self):
        if hasattr(self.request, 'data'):
            username = self.request.data.get("username")
        else:
            username = self.request.POST.get("username")
        ip = self.get_request_ip()
        if is_block_login(username, ip):
            logger.warn('Ip was blocked' + ': ' + username + ':' + ip)
            raise errors.BlockLoginError(username=username, ip=ip)

    def check_user_auth(self):
        request = self.request
        self.check_is_block()
        if hasattr(request, 'data'):
            username = request.data.get('username', '')
            password = request.data.get('password', '')
            public_key = request.data.get('public_key', '')
        else:
            username = request.POST.get('username', '')
            password = request.POST.get('password', '')
            public_key = request.POST.get('public_key', '')
        user, error = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        ip = self.get_request_ip()
        if not user:
            raise errors.CredentialError(
                username=username, error=error, ip=ip, request=request
            )
        clean_failed_count(username, ip)
        request.session['auth_password'] = 1
        request.session['user_id'] = str(user.id)
        return user

    def check_user_mfa_if_need(self, user):
        if self.request.session.get('auth_mfa'):
            return True
        if not user.otp_enabled or not user.otp_secret_key:
            return True
        raise errors.MFARequiredError()

    def check_user_mfa(self, code):
        user = self.get_user_from_session()
        ok = user.check_otp(code)
        if ok:
            self.request.session['auth_mfa'] = 1
            self.request.session['auth_mfa_time'] = time.time()
            self.request.session['auth_mfa_type'] = 'otp'
            return
        raise errors.MFAFailedError(username=user.username, request=self.request)

    def check_user_login_confirm_if_need(self, user):
        from orders.models import LoginConfirmOrder
        confirm_setting = user.get_login_confirm_setting()
        if self.request.session.get('auth_confirm') or not confirm_setting:
            return
        order = None
        if self.request.session.get('auth_order_id'):
            order_id = self.request.session['auth_order_id']
            order = get_object_or_none(LoginConfirmOrder, pk=order_id)
        if not order:
            order = confirm_setting.create_confirm_order(self.request)
            self.request.session['auth_order_id'] = str(order.id)

        if order.status == "accepted":
            return
        elif order.status == "rejected":
            raise errors.LoginConfirmRejectedError(order.id)
        else:
            raise errors.LoginConfirmWaitError(order.id)

    def clear_auth_mark(self):
        self.request.session['auth_password'] = ''
        self.request.session['auth_mfa'] = ''
        self.request.session['auth_confirm'] = ''
        self.request.session['auth_order_id'] = ''

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(
                sender=self.__class__, user=user, request=self.request
            )
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )
