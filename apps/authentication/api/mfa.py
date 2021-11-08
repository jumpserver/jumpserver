# -*- coding: utf-8 -*-
#
import time

from django.utils.translation import ugettext as _
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ValidationError
from rest_framework.response import Response

from common.permissions import IsValidUser, NeedMFAVerify
from common.utils import get_logger
from users.models.user import User
from ..serializers import OtpVerifySerializer
from .. import serializers
from .. import errors
from ..mfa.otp import MFAOtp
from ..mixins import AuthMixin


logger = get_logger(__name__)

__all__ = [
    'MFAChallengeVerifyApi', 'UserOtpVerifyApi', 'SendSMSVerifyCodeApi',
    'MFASendCodeApi'
]


class MFASendCodeApi(AuthMixin, CreateAPIView):
    """
    选择 MFA 后对应操作 api，koko 目前在用
    """
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFASelectTypeSerializer

    def perform_create(self, serializer):
        username = serializer.validated_data.get('username', '')
        mfa_type = serializer.validated_data['type']
        if not username:
            user = self.get_user_from_session()
        else:
            user = get_object_or_404(User, username=username)

        backend_cls = user.get_mfa_backend_by_typ(mfa_type)
        if not backend_cls or not backend_cls.challenge_required:
            raise ValidationError('MFA type not support: {} {}'.format(mfa_type, backend_cls))

        backend = backend_cls(user)
        backend.send_challenge()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
            return Response(serializer.data, status=201)
        except Exception as e:
            logger.exception(e)
            return Response({'error': str(e)}, status=400)


class MFAChallengeVerifyApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFAChallengeSerializer

    def perform_create(self, serializer):
        user = self.get_user_from_session()
        code = serializer.validated_data.get('code')
        mfa_type = serializer.validated_data.get('type', '')
        self.check_user_mfa(code, mfa_type, user)

    def create(self, request, *args, **kwargs):
        try:
            super().create(request, *args, **kwargs)
            return Response({'msg': 'ok'})
        except errors.AuthFailedError as e:
            data = {"error": e.error, "msg": e.msg}
            raise ValidationError(data)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)


class UserOtpVerifyApi(CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = OtpVerifySerializer

    def get(self, request, *args, **kwargs):
        return Response({'code': 'valid', 'msg': 'verified'})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]
        otp = MFAOtp(request.user)

        if otp.check_code(code):
            request.session["MFA_VERIFY_TIME"] = int(time.time())
            return Response({"ok": "1"})
        else:
            return Response({"error": _("Code is invalid")}, status=400)

    def get_permissions(self):
        if self.request.method.lower() == 'get' \
                and settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [NeedMFAVerify]
        return super().get_permissions()


class SendSMSVerifyCodeApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)

    def create(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        username = username.strip()
        if username:
            user = get_object_or_404(User, username=username)
        else:
            user = self.get_user_from_session()
        if not user.mfa_enabled:
            raise errors.NotEnableMFAError
        timeout = user.send_sms_code()
        return Response({'code': 'ok', 'timeout': timeout})
