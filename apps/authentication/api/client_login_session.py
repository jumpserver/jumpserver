from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.utils.crypto import constant_time_compare
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsValidUser
from django.contrib.auth.hashers import check_password
from users.models import Preference
from authentication.backends.drf import OAuth2Authentication
from authentication.services.idle_lock import personal_client_login_policy
from authentication.services.lock_password import (
    MAX_LOCK_PASSWORD_FAILURES, LOCK_PASSWORD_LOGOUT_CODE,
)
from authentication.services.client_login_session import (
    client_login_session_data, is_client_application, revoke_session, client_session_control,
    client_lock_version, clear_client_lock_version,
)


class ClientSessionControlAuthentication(OAuth2Authentication):
    allow_locked_client_session = True


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientSessionStatusView(APIView):
    authentication_classes = (ClientSessionControlAuthentication,)
    permission_classes = (IsValidUser,)
    http_method_names = ('get', 'options')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_client_application(request.auth.application):
            raise PermissionDenied(_('Desktop client authorization required.'))

    def get(self, request):
        session = request.client_login_session
        return Response({
            'client_login_policy': personal_client_login_policy(request.user.pk, session.client_login_policy),
            'client_login_session': client_login_session_data(session),
        }, headers={'Cache-Control': 'no-store'})


class ClientSessionLockView(ClientSessionStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        with client_session_control(request.auth) as session:
            # Even an already-locked session gets a new version: a new lock
            # invalidates any earlier unlock still checking its password.
            version = client_lock_version(session, rotate=True)
            session.is_locked = True
            session.save(update_fields=('is_locked',))
            request.client_login_session = session
            response = self.get(request)
            response.data['lock_version'] = version
            return response


class ClientSessionRevokeView(ClientSessionStatusView):
    http_method_names = ('post', 'options')

    def post(self, request):
        reason = request.data.get('reason', 'logout')
        if reason not in ('logout', 'app_exit'):
            raise serializers.ValidationError({'reason': 'Expected logout or app_exit.'})
        revoke_session(request.client_login_session, reason)
        return Response(status=204)


class ClientUnlockSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    lock_version = serializers.RegexField(r'\A[0-9a-f]{32}\Z', write_only=True)


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class ClientSessionUnlockView(ClientSessionStatusView):
    http_method_names = ('get', 'post', 'options')

    def get(self, request):
        with client_session_control(request.auth) as session:
            configured = Preference.objects.filter(
                user=request.user, category='security', name='lock_password_hash',
            ).exists()
            return Response({
                'has_password': configured,
                'attempts_remaining': max(0, MAX_LOCK_PASSWORD_FAILURES - session.lock_password_failures),
                'settings_path': '/ui/#/profile/security?tab=LockPassword&user_id=' + str(request.user.pk),
                'lock_version': client_lock_version(session, create=True) if session.is_locked else None,
                'client_login_session': client_login_session_data(session),
            }, headers={'Cache-Control': 'no-store'})

    @staticmethod
    def conflict(session):
        return Response({
            'code': 'client_lock_state_changed',
            'lock_version': client_lock_version(session, create=True) if session.is_locked else None,
            'client_login_session': client_login_session_data(session),
        }, status=409, headers={'Cache-Control': 'no-store'})

    def post(self, request):
        serializer = ClientUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credentials = Preference.objects.filter(
            user=request.user, category='security', name='lock_password_hash',
        )
        credential = credentials.first()
        # Password hashing stays outside the shared policy lock. Recheck the
        # credential and login under row locks before committing the result.
        verified = credential is not None and check_password(serializer.validated_data['password'], credential.value)
        with client_session_control(request.auth) as session:
            version = client_lock_version(session)
            if not session.is_locked or not version or not constant_time_compare(
                version, serializer.validated_data['lock_version'],
            ):
                return self.conflict(session)
            current_credential = credentials.select_for_update().first()
            if current_credential is None:
                return Response({'code': 'client_lock_password_unset',
                                 'detail': _('Set a client lock password in the web personal settings first.')}, status=400)
            if credential is None or current_credential.value != credential.value:
                return self.conflict(session)
            if not verified:
                session.lock_password_failures = min(session.lock_password_failures + 1, MAX_LOCK_PASSWORD_FAILURES)
                session.save(update_fields=('lock_password_failures',))
                if session.lock_password_failures >= MAX_LOCK_PASSWORD_FAILURES:
                    clear_client_lock_version(session)
                    revoke_session(session, 'security_revoke')
                    return Response({'code': LOCK_PASSWORD_LOGOUT_CODE, 'logout_after': 5,
                                     'detail': _('Too many incorrect screen lock passwords. This session has been signed out.')}, status=400)
                return Response({'code': 'invalid_client_lock_password',
                                 'attempts_remaining': MAX_LOCK_PASSWORD_FAILURES - session.lock_password_failures,
                                 'detail': _('The client lock password is incorrect.')}, status=400)
            clear_client_lock_version(session)
            session.is_locked = False
            session.lock_password_failures = 0
            session.save(update_fields=('is_locked', 'lock_password_failures'))
            return Response({'verified': True, 'client_login_session': client_login_session_data(session)},
                            headers={'Cache-Control': 'no-store'})
