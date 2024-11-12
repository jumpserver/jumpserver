# -*- coding: utf-8 -*-
#
import uuid

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.exceptions import NotFound

from common.exceptions import JMSException, UnexpectError
from common.permissions import WithBootstrapToken, IsServiceAccount
from common.utils import get_logger
from users.models.user import User
from .. import errors
from .. import serializers
from ..const import MFA_FACE_CONTEXT_CACHE_KEY_PREFIX, MFA_FACE_SESSION_KEY
from ..errors import SessionEmptyError
from ..mixins import AuthMixin

logger = get_logger(__name__)

__all__ = [
    'MFAChallengeVerifyApi', 'MFASendCodeApi',
    'MFAFaceCallbackApi', 'MFAFaceContextApi'
]


class MFAFaceCallbackApi(AuthMixin, CreateAPIView):
    permission_classes = (IsServiceAccount,)
    serializer_class = serializers.MFAFaceCallbackSerializer

    def perform_create(self, serializer):
        token = serializer.validated_data.get('token')
        context = self._get_context_from_cache(token)

        if not serializer.validated_data.get('success', False):
            self._update_context_with_error(
                context,
                serializer.validated_data.get('error_message', 'Unknown error')
            )
            return Response(status=200)

        face_code = serializer.validated_data.get('face_code')
        if not face_code:
            self._update_context_with_error(context, "missing field 'face_code'")
            raise ValidationError({'error': "missing field 'face_code'"})

        self._handle_success(context, face_code)
        return Response(status=200)

    @staticmethod
    def get_face_cache_key(token):
        return f"{MFA_FACE_CONTEXT_CACHE_KEY_PREFIX}_{token}"

    def _get_context_from_cache(self, token):
        cache_key = self.get_face_cache_key(token)
        context = cache.get(cache_key)
        if not context:
            raise ValidationError({'error': "token not exists or expired"})
        return context

    def _update_context_with_error(self, context, error_message):
        context.update({
            'is_finished': True,
            'success': False,
            'error_message': error_message,
        })
        self._update_cache(context)

    def _update_cache(self, context):
        cache_key = self.get_face_cache_key(context['token'])
        cache.set(cache_key, context, 3600)

    def _handle_success(self, context, face_code):
        context.update({
            'is_finished': True,
            'success': True,
            'face_code': face_code
        })
        self._update_cache(context)


class MFAFaceContextApi(AuthMixin, RetrieveAPIView, CreateAPIView):
    permission_classes = (AllowAny,)
    face_token_session_key = MFA_FACE_SESSION_KEY

    @staticmethod
    def get_face_cache_key(token):
        return f"{MFA_FACE_CONTEXT_CACHE_KEY_PREFIX}_{token}"

    def new_face_context(self):
        token = uuid.uuid4().hex
        cache_key = self.get_face_cache_key(token)
        face_context = {
            "token": token,
            "is_finished": False
        }
        cache.set(cache_key, face_context)
        self.request.session[self.face_token_session_key] = token
        return token

    def post(self, request, *args, **kwargs):
        token = self.new_face_context()
        return Response({'token': token})

    def get(self, request, *args, **kwargs):
        token = self.request.session.get('mfa_face_token')

        cache_key = self.get_face_cache_key(token)
        context = cache.get(cache_key)
        if not context:
            raise NotFound({'error': "Token does not exist or has expired."})

        return Response({
            "is_finished": context.get('is_finished', False),
            "success": context.get('success', False),
            "error_message": context.get("error_message", '')
        })


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
            try:
                user = self.get_user_from_session()
            except errors.SessionEmptyError as e:
                raise ValidationError({'error': e})
        else:
            user = self.get_user_from_db(username)

        mfa_backend = user.get_active_mfa_backend_by_type(mfa_type)
        if not mfa_backend or not mfa_backend.challenge_required:
            error = _('Current user not support mfa type: {}').format(mfa_type)
            raise ValidationError({'error': error})

        try:
            mfa_backend.send_challenge()
        except JMSException:
            raise
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
