# -*- coding: utf-8 -*-
#
import time
from datetime import datetime

from django.utils import timezone
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response

from common.permissions import IsValidUser
from ..mfa import MFAOtp
from ..const import ConfirmType
from ..mixins import authenticate
from ..serializers import ConfirmSerializer


class ConfirmViewSet(ListCreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = ConfirmSerializer

    def check(self, confirm_type: str):
        if confirm_type == ConfirmType.MFA:
            return self.user.mfa_enabled

        if confirm_type == ConfirmType.PASSWORD:
            return self.user.is_password_authenticate()

        if confirm_type == ConfirmType.RELOGIN:
            return not self.user.is_password_authenticate()

    def authenticate(self, confirm_type, secret_key):
        if confirm_type == ConfirmType.MFA:
            ok, msg = MFAOtp(self.user).check_code(secret_key)
            return ok, msg

        if confirm_type == ConfirmType.PASSWORD:
            ok = authenticate(self.request, username=self.user.username, password=secret_key)
            msg = '' if ok else _('Authentication failed password incorrect')
            return ok, msg

        if confirm_type == ConfirmType.RELOGIN:
            now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
            now = datetime.strptime(now, '%Y-%m-%d %H:%M:%S')
            login_time = self.request.session.get('login_time')
            SPECIFIED_TIME = 5
            msg = _('Login time has exceeded {} minutes, please login again').format(SPECIFIED_TIME)
            if not login_time:
                return False, msg
            login_time = datetime.strptime(login_time, '%Y-%m-%d %H:%M:%S')
            if (now - login_time).seconds >= SPECIFIED_TIME * 60:
                return False, msg
            return True, ''

    @property
    def user(self):
        return self.request.user

    def list(self, request, *args, **kwargs):
        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            return Response('ok')

        mfa_verify_time = request.session.get('MFA_VERIFY_TIME', 0)
        if time.time() - mfa_verify_time < settings.SECURITY_MFA_VERIFY_TTL:
            return Response('ok')

        data = []
        for i, confirm_type in enumerate(ConfirmType.values, 1):
            if self.check(confirm_type):
                data.append({'name': confirm_type, 'level': i})
        msg = _('This action require verify your MFA')
        return Response({'error': msg, 'backends': data}, status=400)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        confirm_type = validated_data.get('confirm_type')
        secret_key = validated_data.get('secret_key')
        ok, msg = self.authenticate(confirm_type, secret_key)
        if ok:
            request.session["MFA_VERIFY_TIME"] = int(time.time())
            return Response('ok')
        return Response({'error': msg}, status=400)
