from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from django.utils.decorators import method_decorator

from common.permissions import IsValidUser
from authentication.backends.drf import OAuth2Authentication
from authentication.services.client_login_session import (
    client_login_session_data, is_client_application, revoke_session, validate_access_token,
)


class ClientActivityAuthentication(OAuth2Authentication):
    touch_client_login_session = True


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class ClientSessionActivityView(APIView):
    authentication_classes = (ClientActivityAuthentication,)
    permission_classes = (IsValidUser,)

    def get(self, request):
        # Authentication validates the login, but only POST renews idle time.
        if not is_client_application(request.auth.application):
            return Response({'detail': 'Desktop client authorization required.'}, status=403)
        session = request.client_login_session
        return Response({
            'client_login_policy': session.client_login_policy,
            'client_login_session': client_login_session_data(session),
        }, headers={'Cache-Control': 'no-store'})

    def post(self, request):
        # ClientActivityAuthentication already validated and recorded this activity.
        return self.get(request)


class ClientSessionRevokeView(ClientSessionActivityView):
    authentication_classes = (OAuth2Authentication,)
    http_method_names = ('post', 'options')

    def post(self, request):
        reason = request.data.get('reason', 'logout')
        if reason not in ('logout', 'app_exit'):
            raise serializers.ValidationError({'reason': 'Expected logout or app_exit.'})
        if not is_client_application(request.auth.application):
            return Response({'detail': 'Desktop client authorization required.'}, status=403)
        session = validate_access_token(request.auth)
        if session:
            revoke_session(session, reason)
        else:
            # No policy: retain the existing OAuth revocation semantics.
            from oauth2_provider.models import get_refresh_token_model
            refresh = get_refresh_token_model().objects.filter(access_token=request.auth).first()
            (refresh or request.auth).revoke()
        return Response(status=204)
