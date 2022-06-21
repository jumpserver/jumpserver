# -*- coding: utf-8 -*-
#
import time

from django.utils.translation import ugettext_lazy as _
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from rest_framework.response import Response

from authentication.confirm import CONFIRM_BACKENDS
from common.permissions import IsValidUser
from ..const import ConfirmType
from ..serializers import ConfirmSerializer

CONFIRM_BACKEND_MAP = {backend.name: backend for backend in CONFIRM_BACKENDS}


class ConfirmApi(RetrieveAPIView, CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = ConfirmSerializer

    @property
    def user(self):
        return self.request.user

    @property
    def confirm_type(self):
        return self.request.session.get('CONFIRM_TYPE')

    def confirm_backend(self, confirm_type: str):
        user = self.user
        request = self.request
        return CONFIRM_BACKEND_MAP[confirm_type](user, request)

    def retrieve(self, request, *args, **kwargs):
        confirm_type = self.confirm_type
        while True:
            backend = self.confirm_backend(confirm_type)
            if backend.check:
                request.session['CONFIRM_TYPE'] = confirm_type
                return Response({
                    'confirm_type': confirm_type,
                    'content': backend.content
                })
            confirm_type = ConfirmType.next(confirm_type)
            if not confirm_type:
                break
        msg = _('This action require verify your MFA')
        return Response({'error': msg}, status=404)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        mfa_type = validated_data.get('mfa_type')
        secret_key = validated_data.get('secret_key')

        backend = self.confirm_backend(self.confirm_type)
        ok, msg = backend.authenticate(secret_key, mfa_type)
        if ok:
            session_key = f'{self.confirm_type.upper()}_USER_CONFIRM_TIME'
            request.session[session_key] = int(time.time())
            return Response('ok')
        return Response({'error': msg}, status=400)
