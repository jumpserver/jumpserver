from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsValidUser
from django.contrib.auth.hashers import check_password
from rest_framework.throttling import UserRateThrottle
from users.models import Preference
from authentication.backends.drf import OAuth2Authentication
from authentication.services.client_login_session import (
    client_login_session_data, is_client_application, revoke_session, validate_access_token,
)


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientSessionStatusView(APIView):
    authentication_classes = (OAuth2Authentication,)
    permission_classes = (IsValidUser,)
    http_method_names = ('get', 'options')

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_client_application(request.auth.application):
            raise PermissionDenied(_('Desktop client authorization required.'))

    def get(self, request):
        session = request.client_login_session
        return Response({
            'client_login_policy': session.client_login_policy,
            'client_login_session': client_login_session_data(session),
        }, headers={'Cache-Control': 'no-store'})


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


class ClientUnlockThrottle(UserRateThrottle):
    scope = 'client_unlock'
    rate = '5/minute'


@method_decorator(sensitive_post_parameters('password'), name='dispatch')
class ClientSessionUnlockView(ClientSessionStatusView):
    http_method_names = ('get', 'post', 'options')

    def get_throttles(self):
        return [ClientUnlockThrottle()] if self.request.method == 'POST' else []

    def get(self, request):
        configured = Preference.objects.filter(
            user=request.user, category='client', name='client_lock_password_hash',
        ).exists()
        return Response({
            'has_password': configured,
            'settings_path': '/ui/#/profile/password-and-ssh-key?tab=ClientCredentials&user_id=' + str(request.user.pk),
        }, headers={'Cache-Control': 'no-store'})

    def post(self, request):
        serializer = ClientUnlockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = Preference.objects.filter(
            user=request.user, category='client', name='client_lock_password_hash',
        ).first()
        if not credential:
            return Response({'code': 'client_lock_password_unset',
                             'detail': _('Set a client lock password in the web personal settings first.')}, status=400)
        if not check_password(serializer.validated_data['password'], credential.value):
            return Response({'code': 'invalid_client_lock_password',
                             'detail': _('The client lock password is incorrect.')}, status=400)
        session = validate_access_token(request.auth)
        return Response({'verified': True, 'client_login_session': client_login_session_data(session)},
                        headers={'Cache-Control': 'no-store'})
