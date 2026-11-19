from django.core.cache import cache
from django.utils.translation import gettext, gettext as _
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from common.permissions import IsServiceAccount
from common.utils import get_logger, get_object_or_none
from common.utils.lock import DistributedLock
from orgs.utils import tmp_to_root_org
from terminal.api.session.task import create_sessions_tasks
from users.models import User
from .. import serializers
from ..const import (
    FACE_CONTEXT_CACHE_KEY_PREFIX,
    FACE_CONTEXT_CACHE_TTL,
    FACE_MONITOR_CONTEXT_CACHE_TTL,
    FACE_SESSION_KEY,
    FaceMonitorActionChoices,
)
from ..mixins import AuthMixin
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
            raise ValidationError({'error': gettext("missing field 'face_code'")})
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
            raise ValidationError({'error': gettext("token not exists or expired")})
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
                    ids = context.get('connection_token_ids') or [context.get('connection_token_id')]
                    for connection_token_id in sorted(ids):
                        token = ConnectionToken.objects.filter(id=connection_token_id).first()
                        if not token or str(token.user_id) != str(user_id):
                            raise ValidationError({'error': gettext('Face verification does not belong to this connection')})
                        token.complete_acl_requirement('face', face_token=context.get('token'))
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
        session_token = self.request.session.get(self.face_token_session_key)
        requested_token = self.request.query_params.get('token')
        if requested_token and requested_token != session_token:
            raise NotFound({'error': gettext("Token does not belong to the current face capture.")})
        token = requested_token or session_token

        cache_key = self.get_face_cache_key(token)
        context = cache.get(cache_key)
        if not context:
            raise NotFound({'error': gettext("Token does not exist or has expired.")})

        return Response({
            "is_finished": context.get('is_finished', False),
            "success": context.get('success', False),
            "error_message": _(context.get("error_message", ''))
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
        with DistributedLock(cls.get_cache_key(token), expire=5):
            context = cls.get(token)
            if not context:
                context = FaceMonitorContext(token=token, user_id=user_id)
                cache.set(cls.get_cache_key(token), context, FACE_MONITOR_CONTEXT_CACHE_TTL)
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
        with DistributedLock(cache_key, expire=5):
            current = self.get(self.token)
            if not current or str(current.user_id) != str(self.user_id):
                raise ValidationError({'face_monitor_token': _('Online face monitoring context is no longer available')})
            # Two concurrent joins or a monitor callback must not overwrite
            # each other's session registrations with a stale cached object.
            self.session_ids = list(dict.fromkeys(current.session_ids + self.session_ids))
            cache.set(cache_key, self, FACE_MONITOR_CONTEXT_CACHE_TTL)

    def close(self):
        with DistributedLock(self.get_cache_key(self.token), expire=5):
            current = self.get(self.token)
            if current:
                self.session_ids = current.session_ids
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
        if not context:
            raise ValidationError({'face_monitor_token': _('Online face monitoring context is no longer available')})
        from terminal.models import Session
        with tmp_to_root_org():
            session = Session.objects.filter(pk=session_id, is_finished=False, terminal__user=self.request.user).first()
        if not session or str(session.user_id) != str(context.user_id):
            raise PermissionDenied(_('Face monitoring does not belong to this session'))
        context.add_session(str(session.id))

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
                context.save()
                return Response(data={'msg': 'user {} not found'
                                .format(context.user_id)}, status=400)

            if not face_codes or not self._check_face_codes(face_codes, user):
                context.save()
                return Response(data={'msg': gettext('face codes not matched')}, status=400)

        if action == FaceMonitorActionChoices.Pause:
            context.pause_sessions()
        if action == FaceMonitorActionChoices.Resume:
            context.resume_sessions()

        context.save()
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
