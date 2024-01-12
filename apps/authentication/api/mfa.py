# -*- coding: utf-8 -*-
#

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from common.exceptions import UnexpectError
from common.utils import get_logger
from users.models.user import User
from .. import errors
from .. import serializers
from ..errors import SessionEmptyError
from ..mixins import AuthMixin

logger = get_logger(__name__)

__all__ = [
    'MFAChallengeVerifyApi', 'MFASendCodeApi'
]


# MFASelectAPi 原来的名字
class MFASendCodeApi(AuthMixin, CreateAPIView):
    """
    选择 MFA 后对应操作 api，koko 目前在用
    """
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFASelectTypeSerializer
    username = ''
    ip = ''

    def get_user_from_db(self, username):
        """避免暴力测试用户名"""
        ip = self.get_request_ip()
        self.check_mfa_is_block(username, ip)
        try:
            user = get_object_or_404(User, username=username)
            return user
        except Exception as e:
            self.incr_mfa_failed_time(username, ip)
            raise e

    def perform_create(self, serializer):
        username = serializer.validated_data.get('username', '')
        mfa_type = serializer.validated_data['type']

        if not username:
            user = self.get_user_from_session()
        else:
            user = self.get_user_from_db(username)

        mfa_backend = user.get_active_mfa_backend_by_type(mfa_type)
        if not mfa_backend or not mfa_backend.challenge_required:
            error = _('Current user not support mfa type: {}').format(mfa_type)
            raise ValidationError({'error': error})

        try:
            mfa_backend.send_challenge()
        except Exception as e:
            raise UnexpectError(str(e))


class MFAChallengeVerifyApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFAChallengeSerializer

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        try:
            user = self.get_user_from_session()
        except SessionEmptyError:
            user = None
        if not user:
            raise exceptions.NotAuthenticated()

    def perform_create(self, serializer):
        user = self.get_user_from_session()
        code = serializer.validated_data.get('code')
        mfa_type = serializer.validated_data.get('type', '')
        self._do_check_user_mfa(code, mfa_type, user)

    def create(self, request, *args, **kwargs):
        try:
            super().create(request, *args, **kwargs)
            return Response({'msg': 'ok'})
        except errors.AuthFailedError as e:
            data = {"error": e.error, "msg": e.msg}
            return Response(data, status=401)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)
