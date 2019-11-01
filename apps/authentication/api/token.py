# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView

from common.utils import get_request_ip, get_logger, get_object_or_none
from users.utils import (
    check_otp_code, increase_login_failed_count,
    is_block_login, clean_failed_count
)
from users.models import User
from ..utils import check_user_valid
from ..signals import post_auth_success, post_auth_failed
from .. import serializers, errors


logger = get_logger(__name__)

__all__ = ['TokenCreateApi']


class TokenCreateApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.BearerTokenSerializer

    def check_session(self):
        pass

    def get_request_ip(self):
        ip = self.request.data.get('remote_addr', None)
        ip = ip or get_request_ip(self.request)
        return ip

    def check_is_block(self):
        username = self.request.data.get("username")
        ip = self.get_request_ip()
        if is_block_login(username, ip):
            msg = errors.ip_blocked
            logger.warn(msg + ': ' + username + ':' + ip)
            raise errors.AuthFailedError(msg, 'blocked')

    def get_user_from_session(self):
        user_id = self.request.session["user_id"]
        user = get_object_or_none(User, pk=user_id)
        if not user:
            error = "Not user in session: {}".format(user_id)
            raise errors.AuthFailedError(error, 'session_error')
        return user

    def check_user_auth(self):
        request = self.request
        if request.session.get("auth_password") and \
                request.session.get('user_id'):
            user = self.get_user_from_session()
            return user
        self.check_is_block()
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        ip = self.get_request_ip()
        if not user:
            raise errors.AuthFailedError(msg, error='auth_failed', username=username)
        clean_failed_count(username, ip)
        request.session['auth_password'] = 1
        request.session['user_id'] = str(user.id)
        return user

    def check_user_mfa_if_need(self, user):
        if self.request.session.get('auth_mfa'):
            return True
        if not user.otp_enabled or not user.otp_secret_key:
            return True
        otp_code = self.request.data.get("otp_code")
        if not otp_code:
            raise errors.MFARequiredError()
        if not check_otp_code(user.otp_secret_key, otp_code):
            raise errors.AuthFailedError(
                errors.mfa_failed, error='mfa_failed',
                username=user.username,
            )
        return True

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
            raise errors.LoginConfirmRejectedError()
        else:
            raise errors.LoginConfirmWaitError()

    def create(self, request, *args, **kwargs):
        self.check_session()
        # 如果认证没有过，检查账号密码
        try:
            user = self.check_user_auth()
            self.check_user_mfa_if_need(user)
            self.check_user_login_confirm_if_need(user)
            self.send_auth_signal(success=True, user=user)
            resp = super().create(request, *args, **kwargs)
            return resp
        except errors.AuthFailedError as e:
            if e.username:
                increase_login_failed_count(e.username, self.get_request_ip())
                self.send_auth_signal(
                    success=False, username=e.username, reason=e.reason
                )
            return Response({'msg': e.reason, 'error': e.error}, status=401)
        except errors.MFARequiredError:
            msg = _("MFA required")
            data = {'msg': msg, "choices": ["otp"], "error": 'mfa_required'}
            return Response(data, status=300)
        except errors.LoginConfirmRejectedError as e:
            pass
        except errors.LoginConfirmWaitError as e:
            pass
        except errors.LoginConfirmRequiredError as e:
            pass

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
