# -*- coding: utf-8 -*-
#

import uuid

from django.core.cache import cache
from django.utils.translation import ugettext as _
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import CreateAPIView
from drf_yasg.utils import swagger_auto_schema

from common.utils import get_request_ip, get_logger
from users.utils import (
    check_otp_code, increase_login_failed_count,
    is_block_login, clean_failed_count
)
from ..utils import check_user_valid
from ..signals import post_auth_success, post_auth_failed
from .. import serializers


logger = get_logger(__name__)

__all__ = ['TokenCreateApi']


class AuthFailedError(Exception):
    def __init__(self, msg, reason=None):
        self.msg = msg
        self.reason = reason


class MFARequiredError(Exception):
    pass


class TokenCreateApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.BearerTokenSerializer

    @staticmethod
    def check_is_block(username, ip):
        if is_block_login(username, ip):
            msg = _("Log in frequently and try again later")
            logger.warn(msg + ': ' + username + ':' + ip)
            raise AuthFailedError(msg)

    def check_user_valid(self):
        request = self.request
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        if not user:
            raise AuthFailedError(msg)
        return user

    def create(self, request, *args, **kwargs):
        username = self.request.data.get('username')
        ip = self.request.data.get('remote_addr', None)
        ip = ip or get_request_ip(self.request)
        user = None
        try:
            self.check_is_block(username, ip)
            user = self.check_user_valid()
            if user.otp_enabled:
                raise MFARequiredError()
            self.send_auth_signal(success=True, user=user)
            clean_failed_count(username, ip)
            return super().create(request, *args, **kwargs)
        except AuthFailedError as e:
            increase_login_failed_count(username, ip)
            self.send_auth_signal(success=False, user=user, username=username, reason=str(e))
            return Response({'msg': str(e)}, status=401)
        except MFARequiredError:
            msg = _("MFA required")
            seed = uuid.uuid4().hex
            cache.set(seed, user.username, 300)
            resp = {'msg': msg, "choices": ["otp"], "req": seed}
            return Response(resp, status=300)

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
