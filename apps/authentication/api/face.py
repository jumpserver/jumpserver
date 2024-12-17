from django.core.cache import cache
from django.utils.translation import gettext as _
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.serializers import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import NotFound

from common.permissions import IsServiceAccount
from common.utils import get_logger, get_object_or_none
from orgs.utils import tmp_to_root_org
from terminal.api.session.task import create_sessions_tasks
from users.models import User

from .. import serializers
from ..mixins import AuthMixin
from ..const import FACE_CONTEXT_CACHE_KEY_PREFIX, FACE_SESSION_KEY, FACE_CONTEXT_CACHE_TTL, FaceMonitorActionChoices
from ..models import ConnectionToken
from ..serializers.face import FaceMonitorCallbackSerializer, FaceMonitorContextSerializer

logger = get_logger(__name__)

__all__ = [
    'FaceCallbackApi',
    'FaceContextApi',
    'FaceMonitorContext',
    'FaceMonitorContextApi',
    'FaceMonitorCallbackApi'
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
            user_id = context.get('user_id')
            user = User.objects.get(id=user_id)

            if user.check_face(face_code):
                with tmp_to_root_org():
                    connection_token_id = context.get('connection_token_id')
                    token = ConnectionToken.objects.filter(id=connection_token_id).first()
                    token.is_active = True
                    token.save()
            else:
                context.update({
                    'success': False,
                    'error_message': _('Facial comparison failed')
                })
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


class FaceMonitorContext:
    def __init__(self, token, user_id, session_ids=None):
        self.token = token
        self.user_id = user_id
        if session_ids is None:
            self.session_ids = []
        else:
            self.session_ids = session_ids

    @classmethod
    def get_cache_key(cls, token):
        return 'FACE_MONITOR_CONTEXT_{}'.format(token)

    @classmethod
    def get_or_create_context(cls, token, user_id):
        context = cls.get(token)
        if not context:
            context = FaceMonitorContext(token=token,
                                         user_id=user_id)
            context.save()
        return context

    def add_session(self, session_id):
        self.session_ids.append(session_id)
        self.save()

    @classmethod
    def get(cls, token):
        cache_key = cls.get_cache_key(token)
        return cache.get(cache_key, None)

    def save(self):
        cache_key = self.get_cache_key(self.token)
        cache.set(cache_key, self)

    def close(self):
        self.terminal_sessions()
        self._destroy()

    def _destroy(self):
        cache_key = self.get_cache_key(self.token)
        cache.delete(cache_key)

    def pause_sessions(self):
        self._send_task('lock_session')

    def resume_sessions(self):
        self._send_task('unlock_session')

    def terminal_sessions(self):
        self._send_task("kill_session")

    def _send_task(self, task_name):
        create_sessions_tasks(self.session_ids, 'facelive', task_name=task_name)


class FaceMonitorContextApi(CreateAPIView):
    permission_classes = (IsServiceAccount,)
    serializer_class = FaceMonitorContextSerializer

    def perform_create(self, serializer):
        face_monitor_token = serializer.validated_data.get('face_monitor_token')
        session_id = serializer.validated_data.get('session_id')

        context = FaceMonitorContext.get(face_monitor_token)
        context.add_session(session_id)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(status=201)


class FaceMonitorCallbackApi(CreateAPIView):
    permission_classes = (IsServiceAccount,)
    serializer_class = FaceMonitorCallbackSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data.get('token')

        context = FaceMonitorContext.get(token=token)
        is_finished = serializer.validated_data.get('is_finished')
        if is_finished:
            context.close()
            return Response(status=200)

        action = serializer.validated_data.get('action')
        if action == FaceMonitorActionChoices.Verify:
            user = get_object_or_none(User, pk=context.user_id)
            face_codes = serializer.validated_data.get('face_codes')

            if not user:
                return Response(data={'msg': 'user {} not found'
                                .format(context.user_id)}, status=400)

            if not self._check_face_codes(face_codes, user):
                return Response(data={'msg': 'face codes not matched'}, status=400)

        if action == FaceMonitorActionChoices.Pause:
            context.pause_sessions()
        if action == FaceMonitorActionChoices.Resume:
            context.resume_sessions()
        return Response(status=200)

    @staticmethod
    def _check_face_codes(face_codes, user):
        matched = False
        for face_code in face_codes:
            matched = user.check_face(face_code,
                                      distance_threshold=0.45,
                                      similarity_threshold=0.92)
            if matched:
                break
        return matched
