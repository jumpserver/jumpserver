# -*- coding: utf-8 -*-
#
import time

from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

from authentication.permissions import UserConfirmation
from common.api import JMSGenericViewSet
from common.permissions import IsValidUser
from ..const import ConfirmType
from ..schema import (
    CONFIRMATION_BAD_REQUEST_RESPONSE, CONFIRMATION_OK_RESPONSE,
    CONFIRMATION_REQUIRED_RESPONSE, ConfirmationOptionsSerializer,
)
from ..serializers import ConfirmSerializer, ConfirmQuerySerializer


class ConfirmBindORUNBindOAuth(RetrieveAPIView):
    permission_classes = (IsValidUser, UserConfirmation.require(ConfirmType.RELOGIN),)

    def retrieve(self, request, *args, **kwargs):
        return Response('ok')


class UserConfirmationThrottle(UserRateThrottle):
    scope = 'user_confirmation'
    rate = '5/minute'


class UserConfirmationViewSet(JMSGenericViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = ConfirmSerializer

    def get_throttles(self):
        throttles = super().get_throttles()
        if self.request.method == 'POST':
            throttles.append(UserConfirmationThrottle())
        return throttles

    @extend_schema(
        parameters=[ConfirmQuerySerializer],
        description=(
            'Check whether the current session has a sufficient, unexpired confirmation for the current user. '
            'For MFA reset, explicitly set confirm_type=mfa; the default password check is insufficient. '
            'Send the same authentication credentials and session cookie used for confirmation.'
        ),
        responses={200: CONFIRMATION_OK_RESPONSE, 400: CONFIRMATION_BAD_REQUEST_RESPONSE,
                   412: CONFIRMATION_REQUIRED_RESPONSE},
    )
    @action(methods=['get'], detail=False)
    def check(self, request):
        confirm_type = self.get_query_confirm_type()
        permission = UserConfirmation.require(confirm_type)()
        permission.has_permission(request, self)
        return Response('ok')

    def get_query_confirm_type(self):
        serializer = ConfirmQuerySerializer(data=self.request.query_params)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data['confirm_type']

    def unavailable_confirmation_response(self):
        message = _('No available confirmation method for the current user. Configure and enable MFA, then retry.')
        return Response({'error': message}, status=status.HTTP_400_BAD_REQUEST)

    def get_confirm_backend(self, confirm_type):
        backend_classes = ConfirmType.get_prop_backends(confirm_type)
        if not backend_classes:
            return

        for backend_cls in backend_classes:
            backend = backend_cls(self.request.user, self.request)
            if not backend.check():
                continue
            return backend

    @extend_schema(
        parameters=[ConfirmQuerySerializer],
        description=(
            'Discover an available confirmation method for the current user. confirm_type is the minimum '
            'required level (relogin < password < mfa); the response may select a stronger method. '
            'Submit the returned confirm_type to POST /api/v1/authentication/confirm/. For MFA, select a '
            'content entry with disabled=false and use its name as mfa_type. If no method is available, '
            'configure and enable MFA for the current operator. For relogin, relogin_required indicates '
            'whether a fresh login is needed. Explain the effect before asking the user to leave the '
            'current session. This request does not confirm identity.'
        ),
        responses={200: ConfirmationOptionsSerializer, 400: CONFIRMATION_BAD_REQUEST_RESPONSE},
    )
    def list(self, request, *args, **kwargs):
        confirm_type = self.get_query_confirm_type()
        backend = self.get_confirm_backend(confirm_type)
        if backend is None:
            return self.unavailable_confirmation_response()

        data = {
            'confirm_type': backend.name,
            'content': backend.content,
        }
        if backend.name == ConfirmType.RELOGIN:
            data['relogin_required'] = not backend.authenticate(None, None)[0]
        return Response(data=data)

    @extend_schema(
        description=(
            'Confirm the identity of the current operator. Discover the method with GET first. '
            'confirm_type is required and must not be blank. MFA confirmation requires mfa_type to identify '
            'an active method allowed for this user; code-based methods also require a non-empty secret_key. '
            'Password confirmation requires secret_key. Face confirmation uses its existing verification '
            'context; passkeys use the separate passkey authentication flow. Invalid input returns JSON 400. '
            'Confirmation submissions are limited to five per minute per user; excess requests return HTTP 429.\n\n'
            'A successful response is HTTP 200 with the JSON string "ok". Save the response session cookie '
            'and send it with subsequent requests, even when using a Bearer token. Confirmation is bound to '
            'the current user and this session. MFA confirmation uses SECURITY_MFA_VERIFY_TTL (default 3600 '
            'seconds); password confirmation lasts 300 seconds. Relogin confirmation reuses only the first '
            '300 seconds after the original Session authentication and does not extend that window. All confirmation is '
            'subject to session expiry. A relogin that is no longer recent returns code=relogin_required. '
            'Password confirmation does not satisfy an operation requiring MFA. Use '
            'GET /api/v1/authentication/confirm/check/?confirm_type=mfa to check MFA confirmation.'
        ),
        examples=[OpenApiExample(
            'Confirm with the current operator OTP', request_only=True,
            value={'confirm_type': 'mfa', 'mfa_type': 'otp', 'secret_key': '<current operator OTP code>'},
        )],
        responses={200: CONFIRMATION_OK_RESPONSE, 400: CONFIRMATION_BAD_REQUEST_RESPONSE,
                   429: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}},
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        confirm_type = validated_data['confirm_type']
        mfa_type = validated_data.get('mfa_type')
        secret_key = validated_data.get('secret_key')

        backend = self.get_confirm_backend(confirm_type)
        if backend is None:
            return self.unavailable_confirmation_response()
        ok, msg = backend.authenticate(secret_key, mfa_type)
        if ok:
            request.session['CONFIRM_LEVEL'] = ConfirmType.values.index(confirm_type) + 1
            request.session['CONFIRM_TYPE'] = confirm_type
            # Reusing a recent login must not renew the original five-minute window.
            confirmed_at = backend.login_timestamp if backend.name == ConfirmType.RELOGIN else time.time()
            request.session['CONFIRM_TIME'] = int(confirmed_at)
            request.session['CONFIRM_USER_ID'] = str(request.user.pk)
            return Response('ok')
        error = {'error': msg}
        if backend.name == ConfirmType.RELOGIN:
            error['code'] = 'relogin_required'
        return Response(error, status=status.HTTP_400_BAD_REQUEST)
