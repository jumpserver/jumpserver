from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.hashers import check_password
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from audits.models import UserSession
from authentication.backends.drf import SessionAuthentication
from authentication.services.idle_lock import personal_idle_lock_time, effective_idle_lock_time, idle_lock_limits
from authentication.services.lock_password import (
    MAX_LOCK_PASSWORD_FAILURES, LOCK_PASSWORD_LOGOUT_CODE, record_lock_password_failure,
)
from authentication.services.web_session_lock import session_locked, session_scope, lock_cache_key
from common.permissions import IsValidUser
from common.sessions import session_expiry
from common.utils import get_request_ip
from users.models import Preference


class WebSessionControlAuthentication(SessionAuthentication):
    allow_locked_web_session = True


class WebUnlockSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class WebSessionLockStatusView(APIView):
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
        key = request.session.session_key
        session = UserSession.objects.filter(key=key, user=request.user).first()
        expires = session_expiry(key)
        idle_limit = idle_lock_limits(use_cache=True)['web_idle_lock_time']
        return Response({
            'scope': session_scope(key),
            'locked': session_locked(key, request.user.pk),
            'has_password': Preference.objects.filter(user=request.user, category='client', name='client_lock_password_hash').exists(),
            'attempts_remaining': max(0, MAX_LOCK_PASSWORD_FAILURES - (session.lock_password_failures if session else 0)),
            'idle_lock_time': effective_idle_lock_time(
                idle_limit,
                personal_idle_lock_time(request.user.pk, 'web_idle_lock_time'),
            ),
            'idle_lock_time_limit': idle_limit,
            'authenticated_at': session.date_created.isoformat() if session and session.date_created else None,
            'expires_at': expires.isoformat() if expires else None,
            'max_expires_at': None,
            'session_timeout': settings.SESSION_COOKIE_AGE,
            'sliding_expiry': settings.SESSION_SAVE_EVERY_REQUEST,
            'expire_at_browser_close': request.session.get_expire_at_browser_close(),
            'server_time': timezone.now().isoformat(),
            'user': {'id': str(request.user.pk), 'name': request.user.name, 'username': request.user.username},
        }, headers={'Cache-Control': 'no-store'})


class WebSessionLockView(WebSessionLockStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        key = request.session.session_key
        with transaction.atomic():
            updated = UserSession.objects.filter(key=key, user=request.user).update(is_locked=True)
            if not updated:
                UserSession.objects.create(user=request.user, key=key, is_locked=True, type='W',
                                           ip=get_request_ip(request), user_agent=request.META.get('HTTP_USER_AGENT', '')[:254])
            transaction.on_commit(lambda: cache.set(lock_cache_key(key), True, timeout=60))
        return self.get(request)


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class WebSessionUnlockView(WebSessionLockStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        serializer = WebUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = Preference.objects.filter(user=request.user, category='client', name='client_lock_password_hash').first()
        if credential is None:
            return Response({'code': 'lock_password_unset', 'detail': _('Set a lock password after signing in again.')}, status=400)
        key = request.session.session_key
        if not check_password(serializer.validated_data['password'], credential.value):
            record, _created = UserSession.objects.get_or_create(
                key=key, user=request.user,
                defaults={'ip': get_request_ip(request), 'type': 'W', 'is_locked': True},
            )
            failures = record_lock_password_failure(record)
            if failures >= MAX_LOCK_PASSWORD_FAILURES:
                logout(request)
                cache.delete(lock_cache_key(key))
                return Response({'code': LOCK_PASSWORD_LOGOUT_CODE, 'logout_after': 5,
                                 'detail': _('Too many incorrect screen lock passwords. This session has been signed out.')}, status=400)
            return Response({'code': 'invalid_lock_password',
                             'attempts_remaining': MAX_LOCK_PASSWORD_FAILURES - failures,
                             'detail': _('The lock password is incorrect.')}, status=400)
        with transaction.atomic():
            UserSession.objects.filter(key=key, user=request.user).update(is_locked=False, lock_password_failures=0)
            transaction.on_commit(lambda: cache.set(lock_cache_key(key), False, timeout=60))
        return self.get(request)


class WebSessionLockLogoutView(WebSessionLockStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        key = request.session.session_key
        logout(request)
        cache.delete(lock_cache_key(key))
        return Response({'login_url': str(settings.LOGIN_URL)})
