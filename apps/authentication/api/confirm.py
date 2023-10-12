# -*- coding: utf-8 -*-
#
import time

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from rest_framework.response import Response

from authentication.permissions import UserConfirmation
from common.permissions import IsValidUser
from ..const import ConfirmType
from ..serializers import ConfirmSerializer


class ConfirmBindORUNBindOAuth(RetrieveAPIView):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)

    def retrieve(self, request, *args, **kwargs):
        return Response('ok')


class ConfirmApi(RetrieveAPIView, CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = ConfirmSerializer

    def get_confirm_backend(self, confirm_type):
        backend_classes = ConfirmType.get_prop_backends(confirm_type)
        if not backend_classes:
            return
        for backend_cls in backend_classes:
            backend = backend_cls(self.request.user, self.request)
            if not backend.check():
                continue
            return backend

    def retrieve(self, request, *args, **kwargs):
        confirm_type = request.query_params.get('confirm_type', 'password')
        backend = self.get_confirm_backend(confirm_type)
        if backend is None:
            msg = _('This action require verify your MFA')
            return Response(data={'error': msg}, status=status.HTTP_404_NOT_FOUND)

        data = {
            'confirm_type': backend.name,
            'content': backend.content,
        }
        return Response(data=data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        confirm_type = validated_data.get('confirm_type', 'password')
        mfa_type = validated_data.get('mfa_type')
        secret_key = validated_data.get('secret_key')

        backend = self.get_confirm_backend(confirm_type)
        ok, msg = backend.authenticate(secret_key, mfa_type)
        if ok:
            request.session['CONFIRM_LEVEL'] = ConfirmType.values.index(confirm_type) + 1
            request.session['CONFIRM_TIME'] = int(time.time())
            return Response('ok')
        return Response({'error': msg}, status=400)
