from django.core.cache import cache
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound

from common.permissions import IsServiceAccount
from common.utils import get_logger
from orgs.utils import tmp_to_root_org

from .. import serializers
from ..mixins import AuthMixin
from ..const import FACE_CONTEXT_CACHE_KEY_PREFIX, FACE_SESSION_KEY, FACE_CONTEXT_CACHE_TTL
from ..models import ConnectionToken

logger = get_logger(__name__)

__all__ = [
    'FaceCallbackApi', 'FaceContextApi'
]


class FaceCallbackApi(AuthMixin, CreateAPIView):
    permission_classes = (IsServiceAccount,)
    serializer_class = serializers.FaceCallbackSerializer

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
        try:
            self._handle_success(context, face_code)
        except Exception as e:
            self._update_context_with_error(context, str(e))
        return Response(status=200)

    @staticmethod
    def get_face_cache_key(token):
        return f"{FACE_CONTEXT_CACHE_KEY_PREFIX}_{token}"

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
        cache.set(cache_key, context, FACE_CONTEXT_CACHE_TTL)

    def _handle_success(self, context, face_code):
        context.update({
            'is_finished': True,
            'success': True,
            'face_code': face_code
        })
        action = context.get('action', None)
        if action == 'login_asset':
            with tmp_to_root_org():
                connection_token_id = context.get('connection_token_id')
                token = ConnectionToken.objects.filter(id=connection_token_id).first()
                token.is_active = True
                token.save()
        self._update_cache(context)


class FaceContextApi(AuthMixin, RetrieveAPIView, CreateAPIView):
    permission_classes = (AllowAny,)
    face_token_session_key = FACE_SESSION_KEY

    @staticmethod
    def get_face_cache_key(token):
        return f"{FACE_CONTEXT_CACHE_KEY_PREFIX}_{token}"

    def new_face_context(self):
        return self.create_face_verify_context()

    def post(self, request, *args, **kwargs):
        token = self.new_face_context()
        return Response({'token': token})

    def get(self, request, *args, **kwargs):
        token = self.request.session.get(self.face_token_session_key)

        cache_key = self.get_face_cache_key(token)
        context = cache.get(cache_key)
        if not context:
            raise NotFound({'error': "Token does not exist or has expired."})

        return Response({
            "is_finished": context.get('is_finished', False),
            "success": context.get('success', False),
            "error_message": context.get("error_message", '')
        })
