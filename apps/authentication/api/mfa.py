# -*- coding: utf-8 -*-
#
import time
from rest_framework.permissions import AllowAny
from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ValidationError
from rest_framework.response import Response

from common.permissions import IsValidUser
from ..serializers import OtpVerifySerializer
from .. import serializers
from .. import errors
from ..mixins import AuthMixin


__all__ = ['MFAChallengeApi', 'UserOtpVerifyApi']


class MFAChallengeApi(AuthMixin, CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.MFAChallengeSerializer

    def perform_create(self, serializer):
        try:
            user = self.get_user_from_session()
            code = serializer.validated_data.get('code')
            valid = user.check_mfa(code)
            if not valid:
                self.request.session['auth_mfa'] = ''
                raise errors.MFAFailedError(
                    username=user.username, request=self.request
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["code"]

        if request.user.check_mfa(code):
            request.session["MFA_VERIFY_TIME"] = int(time.time())
            return Response({"ok": "1"})
        else:
            return Response({"error": "Code not valid"}, status=400)
