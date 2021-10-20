# -*- coding: utf-8 -*-
#
import builtins
import time

from django.utils.translation import ugettext as _
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ValidationError
from rest_framework.response import Response

from common.permissions import IsValidUser, NeedMFAVerify
from users.models.user import MFAType, User
from ..serializers import OtpVerifySerializer
from .. import serializers
from .. import errors
from ..mixins import AuthMixin


__all__ = ['MFAChallengeApi', 'UserOtpVerifyApi', 'SendSMSVerifyCodeApi', 'MFASelectTypeApi']


class MFASelectTypeApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFASelectTypeSerializer

    def perform_create(self, serializer):
        mfa_type = serializer.validated_data['type']
        if mfa_type == MFAType.SMS_CODE:
            user = self.get_user_from_session()
            user.send_sms_code()


class MFAChallengeApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFAChallengeSerializer

    def perform_create(self, serializer):
        try:
            user = self.get_user_from_session()
            code = serializer.validated_data.get('code')
            mfa_type = serializer.validated_data.get('type', MFAType.OTP)

            valid = user.check_mfa(code, mfa_type=mfa_type)
            if not valid:
                self.request.session['auth_mfa'] = ''
                raise errors.MFAFailedError(
                    username=user.username, request=self.request, ip=self.get_request_ip()
                )
            else:
                self.request.session['auth_mfa'] = '1'
        except errors.AuthFailedError as e:
            data = {"error": e.error, "msg": e.msg}
            raise ValidationError(data)
        except errors.NeedMoreInfoError as e:
            return Response(e.as_data(), status=200)

    def create(self, request, *args, **kwargs):
        super().create(request, *args, **kwargs)
        return Response({'msg': 'ok'})


class UserOtpVerifyApi(CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = OtpVerifySerializer

    def get(self, request, *args, **kwargs):
        return Response({'code': 'valid', 'msg': 'verified'})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        if request.user.check_mfa(code):
            request.session["MFA_VERIFY_TIME"] = int(time.time())
            return Response({"ok": "1"})
        else:
            return Response({"error": _("Code is invalid")}, status=400)

    def get_permissions(self):
        if self.request.method.lower() == 'get' and settings.SECURITY_VIEW_AUTH_NEED_MFA:
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
