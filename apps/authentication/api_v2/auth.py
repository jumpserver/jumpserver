# -*- coding: utf-8 -*-
#
import time

from django.core.cache import cache
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.translation import ugettext as _

from common.utils import get_logger, get_request_ip, get_object_or_none
from users.utils import (
    check_user_valid, check_otp_code, increase_login_failed_count,
    is_block_login, clean_failed_count
)
from users.models import User
from assets.models import Asset, SystemUser
from audits.models import UserLoginLog as LoginLog
from .. import serializers_v2 as serializers
from ..signals import post_auth_success, post_auth_failed

logger = get_logger(__file__)


class UserTokenApi(generics.CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.UserTokenSerializer

    def post(self, request):
        # limit login
        username = request.data.get('username')
        ip = request.data.get('remote_addr', None)
        ip = ip or get_request_ip(request)

        if is_block_login(username, ip):
            msg = _("Log in frequently and try again later")
            logger.warn(msg + ': ' + username + ':' + ip)
            return Response({'msg': msg}, status=401)

        user, msg = self.check_user_valid(request)
        if not user:
            username = request.data.get('username', '')
            exist = User.objects.filter(username=username).first()
            reason = LoginLog.REASON_PASSWORD if exist else LoginLog.REASON_NOT_EXIST
            self.send_auth_signal(success=False, username=username, reason=reason)
            increase_login_failed_count(username, ip)
            return Response({'msg': msg}, status=401)

        if user.password_has_expired:
            self.send_auth_signal(
                success=False, username=username,
                reason=LoginLog.REASON_PASSWORD_EXPIRED
            )
            msg = _("The user {} password has expired, please update.".format(
                user.username))
            logger.info(msg)
            return Response({'msg': msg}, status=401)

        if not user.otp_enabled:
            self.send_auth_signal(success=True, user=user)
            # 登陆成功，清除原来的缓存计数
            clean_failed_count(username, ip)
            token = user.create_bearer_token(request)
            return Response(
                {'token': token, 'user': self.serializer_class(user).data}
            )

        seed = uuid.uuid4().hex
        cache.set(seed, user, 300)
        return Response(
            {
                'code': 101,
                'msg': _('Please carry seed value and '
                         'conduct MFA secondary certification'),
                'otp_url': reverse('api-auth:user-otp-auth'),
                'seed': seed,
                'user': self.serializer_class(user).data
            }, status=300
        )

    @staticmethod
    def check_user_valid(request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        return user, msg

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(sender=self.__class__, user=user, request=self.request)
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )


class UserMFAAuthApi(generics.RetrieveAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = serializers.MFAAuthSerializer
    mfa_auth_choices = ["otp"]

    def retrieve(self, request, *args, **kwargs):
        data = {
            "choices": self.mfa_auth_choices,
            "last_auth_time": request.session.get("MFA_LAST_AUTH_TIME")
        }
        serializer = self.serializer_class(data)
        return Response(serializer.data)


class UserOTPAuthApi(generics.CreateAPIView):
    permission_classes = (permissions.AllowAny,)
    serializer_class = serializers.OTPAuthSerializer

    MFA_TOKEN_CACHE_PREFIX = "MFA_TOKEN_"

    def get_user_from_mfa_token(self, token):
        key = self.MFA_TOKEN_CACHE_PREFIX + token
        user_id = cache.get(key)
        if not user_id:
            return None
        return get_object_or_none(User, id=user_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        if request.user.is_authenticated:
            user = request.user
        elif serializer.get("mfa_token"):
            token = serializer["mfa_token"]
            user = self.get_user_from_mfa_token(token)
            if not user:
                data = {
                    "code": "mfa_token_error",
                    "error": 'Mfa token error or expired',
                }
                return Response(data, status=401)
        else:
            data = {
                "code": "mfa_token_required",
                "error": _('Please login with username/password first'),
            }
            return Response(data, status=401)

        if not user.check_otp(code):
            self.send_auth_signal(success=False, username=user.username,
                                  reason=LoginLog.REASON_MFA)
            data = {'msg': _('OTP code error')}
            return Response(data, status=401)
        request.session["MFA_LAST_AUTH_TIME"] = int(time.time())
        self.send_auth_signal(success=True, username=user.username,
                              reason=LoginLog.REASON_MFA)
        return Response(status=400)

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(sender=self.__class__, user=user, request=self.request)
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )
