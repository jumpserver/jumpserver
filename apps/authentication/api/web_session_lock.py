import re
from datetime import datetime, timezone as datetime_timezone

from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.contrib.sessions.backends.base import UpdateError
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.backends.drf import SessionAuthentication
from authentication.services.idle_lock import personal_idle_lock_time, effective_idle_lock_time, idle_lock_limits
from authentication.services.lock_password import (
    MAX_LOCK_PASSWORD_FAILURES, LOCK_PASSWORD_LOGOUT_CODE,
)
from authentication.services.web_session_lock import session_scope
from common.permissions import IsValidUser
from common.sessions import SessionStateConflict, normalize_security_state
from users.models import Preference


class WebSessionControlAuthentication(SessionAuthentication):
    allow_locked_web_session = True


class WebUnlockSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class WebSessionStatusView(APIView):
    authentication_classes = (WebSessionControlAuthentication,)
    permission_classes = (IsValidUser,)

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method == 'POST':
            scope = request.data.get('scope')
            if not isinstance(scope, str) or not constant_time_compare(scope, session_scope(request.session.session_key)):
                error = APIException({'code': 'web_session_changed'})
                error.status_code = 409
                raise error

    def get(self, request):
        try:
            with request.session.control():
                page_id = request.headers.get('X-JMS-Page-ID')
                if page_id is not None:
                    if not re.fullmatch(r'[a-zA-Z0-9-]{1,128}', page_id):
                        raise serializers.ValidationError({'page_id': 'Invalid page ID.'})
                    request.session.update_page(page_id, entering=True)
                return self.status(request)
        except UpdateError:
            raise NotAuthenticated()

    def check_version(self, request):
        version = request.data.get('expected_version')
        if type(version) is not int or not 0 <= version <= 9007199254740991:
            raise serializers.ValidationError({'expected_version': 'A non-negative integer is required.'})
        if version != request.session.login_policy['state_version']:
            return self.conflict(request)

    def conflict(self, request):
        return Response({
            'code': 'web_session_state_conflict', 'session': self.status(request).data,
        }, status=409, headers={'Cache-Control': 'no-store'})

    def set_locked(self, request, locked):
        try:
            request.session.set_locked(locked, request.data['expected_version'])
        except SessionStateConflict:
            return self.conflict(request)

    def status(self, request):
        key = request.session.session_key
        expires = request.session.get_expiry_date()
        idle_limit = idle_lock_limits(use_cache=True)['web_idle_lock_time']
        policy = request.session.login_policy
        maximum = (datetime.fromtimestamp(policy['expires_at'], tz=datetime_timezone.utc)
                   if not policy['renew'] else None)
        authenticated_at = datetime.fromtimestamp(policy['authenticated_at'], tz=datetime_timezone.utc)
        policy = normalize_security_state(policy)
        return Response({
            'scope': session_scope(key),
            'state_version': policy['state_version'],
            'unlocked_at': (datetime.fromtimestamp(policy['unlocked_at'], tz=datetime_timezone.utc).isoformat()
                            if policy.get('unlocked_at') else None),
            'locked': policy['locked'],
            'has_password': Preference.objects.filter(user=request.user, category='security', name='lock_password_hash').exists(),
            'attempts_remaining': max(0, MAX_LOCK_PASSWORD_FAILURES - policy['lock_password_failures']),
            'idle_lock_time': effective_idle_lock_time(
                idle_limit,
                personal_idle_lock_time(request.user.pk, 'web_idle_lock_time'),
            ),
            'idle_lock_time_limit': idle_limit,
            'authenticated_at': authenticated_at.isoformat(),
            'expires_at': expires.isoformat() if expires else None,
            'max_expires_at': maximum.isoformat() if maximum else None,
            'session_timeout': policy['duration'],
            'sliding_expiry': policy['renew'],
            'expire_at_browser_close': request.session.get_expire_at_browser_close(),
            'server_time': timezone.now().isoformat(),
            'user': {'id': str(request.user.pk), 'name': request.user.name, 'username': request.user.username},
        }, headers={'Cache-Control': 'no-store'})


class WebSessionLockView(WebSessionStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        try:
            with request.session.control():
                if conflict := self.check_version(request):
                    return conflict
                if conflict := self.set_locked(request, True):
                    return conflict
                return self.status(request)
        except UpdateError:
            raise NotAuthenticated()


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class WebSessionUnlockView(WebSessionStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        serializer = WebUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            with request.session.control():
                if conflict := self.check_version(request):
                    return conflict
                if not request.session.login_policy['locked']:
                    return self.status(request)
                credential = Preference.objects.filter(
                    user=request.user, category='security', name='lock_password_hash',
                ).first()
                if credential is None:
                    return Response({'code': 'lock_password_unset',
                                     'detail': _('Set a lock password after signing in again.')}, status=400)
                if not check_password(serializer.validated_data['password'], credential.value):
                    failures = request.session.record_lock_password_failure(request.data['expected_version'])
                    if failures >= MAX_LOCK_PASSWORD_FAILURES:
                        logout(request)
                        return Response({'code': LOCK_PASSWORD_LOGOUT_CODE, 'logout_after': 5,
                                         'detail': _('Too many incorrect screen lock passwords. This session has been signed out.')}, status=400)
                    return Response({'code': 'invalid_lock_password',
                                     'state_version': request.session.login_policy['state_version'],
                                     'attempts_remaining': MAX_LOCK_PASSWORD_FAILURES - failures,
                                     'detail': _('The lock password is incorrect.')}, status=400)
                if conflict := self.set_locked(request, False):
                    return conflict
                return self.status(request)
        except SessionStateConflict:
            return self.conflict(request)
        except UpdateError:
            raise NotAuthenticated()
