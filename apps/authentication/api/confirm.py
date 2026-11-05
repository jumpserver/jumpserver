# -*- coding: utf-8 -*-
#
import time

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from authentication.services.lock_password import (
    LOCK_PASSWORD_PURPOSE, LockPasswordConfirmation, LockPasswordConfirmationThrottle,
    confirmation_type, mark_lock_password_confirmation,
)

from authentication.permissions import UserConfirmation
from common.api import JMSGenericViewSet
from common.permissions import IsValidUser
from ..const import ConfirmType
from ..serializers import ConfirmSerializer


class ConfirmBindORUNBindOAuth(RetrieveAPIView):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)

    def retrieve(self, request, *args, **kwargs):
        return Response('ok')


class UserConfirmationViewSet(JMSGenericViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = ConfirmSerializer

    def get_throttles(self):
        if self.request.method == 'POST' and self.lock_password_purpose():
            return [LockPasswordConfirmationThrottle()]
        return super().get_throttles()

    @action(methods=['get'], detail=False)
    def check(self, request):
        confirm_type = request.query_params.get('confirm_type', 'password')
        permission = (LockPasswordConfirmation() if request.query_params.get('purpose') == LOCK_PASSWORD_PURPOSE
                      else UserConfirmation.require(confirm_type)())
        permission.has_permission(request, self)
        return Response('ok')

    def lock_password_purpose(self):
        return (self.request.query_params.get('purpose') or self.request.data.get('purpose')) == LOCK_PASSWORD_PURPOSE

    def get_confirm_backend(self, confirm_type):
        if self.lock_password_purpose():
            from authentication.confirm import CONFIRM_BACKEND_MAP
            required = confirmation_type(self.request.user)
            if confirm_type != required:
                raise ValidationError({'confirm_type': required})
            backend = CONFIRM_BACKEND_MAP[required](self.request.user, self.request)
            # A configured email/MFA factor can verify identity even when login MFA is optional.
            available = bool(self.request.user.active_mfa_backends) if required == 'mfa' else backend.check()
            return backend if available else None
        backend_classes = ConfirmType.get_prop_backends(confirm_type)
        if not backend_classes:
            return

        for backend_cls in backend_classes:
            backend = backend_cls(self.request.user, self.request)
            if not backend.check():
                continue
            return backend

    def list(self, request, *args, **kwargs):
        confirm_type = request.query_params.get('confirm_type', 'password')
        backend = self.get_confirm_backend(confirm_type)
        if backend is None:
            msg = (_('Configure an identity verification method before changing the lock password.')
                   if self.lock_password_purpose() else _('This action require verify your MFA'))
            return Response(data={'error': msg}, status=status.HTTP_400_BAD_REQUEST)

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
        if backend is None:
            return Response({'error': _('Configure an identity verification method before changing the lock password.')}, status=400)
        if (self.lock_password_purpose() and confirm_type == 'mfa'
                and mfa_type not in request.user.active_mfa_backends_mapper):
            raise ValidationError({'mfa_type': _('This verification method is not available.')})
        ok, msg = backend.authenticate(secret_key, mfa_type)
        if ok:
            request.session['CONFIRM_LEVEL'] = ConfirmType.values.index(confirm_type) + 1
            request.session['CONFIRM_TYPE'] = confirm_type
            request.session['CONFIRM_TIME'] = int(time.time())
            request.session['CONFIRM_USER_ID'] = str(request.user.pk)
            if self.lock_password_purpose():
                mark_lock_password_confirmation(request, confirm_type)
            return Response('ok')
        return Response({'error': msg}, status=400)
