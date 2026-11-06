# ~*~ coding: utf-8 ~*~
from django.db import transaction
from django.utils.decorators import method_decorator
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from authentication.models import ConnectionToken
from authentication.backends.drf import SessionAuthentication
from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from common.permissions import IsValidUser
from authentication.permissions import IsValidUserOrConnectionToken
from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org
from users.notifications import (
    ResetPasswordMsg, ResetPasswordSuccessMsg, ResetSSHKeyMsg,
)
from .mixins import UserQuerysetMixin
from .. import serializers
from ..models import User

__all__ = [
    'UserResetPasswordApi', 'UserResetPKApi',
    'UserProfileApi', 'UserPasswordApi',
    'UserPermissionsApi', 'UserLockPasswordApi',
    'UserFileEncryptionApi', 'UserIdleLockApi'
]


class UserResetPasswordApi(UserQuerysetMixin, generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        ResetPasswordMsg(user).publish_async()


class UserResetPKApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = None
        user.save()
        user.ssh_keys.update(is_active=False)
        ResetSSHKeyMsg(user).publish_async()


class UserProfileApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsValidUserOrConnectionToken,)
    serializer_class = serializers.UserProfileSerializer

    def get_object(self):
        if self.request.user.is_anonymous:
            user = self.get_connection_token_user()
            if user:
                return user
        return self.request.user

    def get_connection_token_user(self):
        token_id = self.request.query_params.get('token')
        if not token_id:
            return
        with tmp_to_root_org():
            token = get_object_or_none(ConnectionToken, id=token_id)
        if not token:
            return
        return token.user


class UserPasswordApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePasswordSerializer
    # patch 方法不允许，否则 old_password 不传会导致用户直接修改密码成功，安全风险大
    http_method_names = ['put', 'head', 'options']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        ResetPasswordSuccessMsg(self.request.user, request).publish_async()
        return resp


class UserPermissionsApi(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserPermsSerializer

    def get_object(self):
        return self.request.user


class BaseUserPasswordSettingsApi(generics.RetrieveUpdateAPIView):
    """Shared web-session validation for lock and file-encryption password settings."""
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsValidUser,)
    http_method_names = ('get', 'patch', 'head', 'options')

    def get_object(self):
        return {}


class UserLockPasswordApi(BaseUserPasswordSettingsApi):
    serializer_class = serializers.UserLockPasswordSerializer

    def perform_update(self, serializer):
        # Check parsed changes, not raw input: e.g. clear="true" is a real mutation,
        # while an empty PATCH and form metadata do not require confirmation.
        if serializer.validated_data.get('password') or serializer.validated_data.get('clear'):
            UserConfirmation.require(ConfirmType.RELOGIN)().has_permission(self.request, self)
        super().perform_update(serializer)


class UserFileEncryptionApi(BaseUserPasswordSettingsApi):
    serializer_class = serializers.UserFileEncryptionSerializer


@method_decorator(transaction.non_atomic_requests, name='dispatch')
class UserIdleLockApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.UserIdleLockSerializer
    http_method_names = ('get', 'patch', 'head', 'options')

    def get_object(self):
        from authentication.services.idle_lock import idle_lock_preferences
        return idle_lock_preferences(self.request.user.pk)

    def update(self, request, *args, **kwargs):
        from authentication.services.client_login_session import client_policy_lock

        # Share the existing policy lock so validation and administrator clamping agree.
        with client_policy_lock(), transaction.atomic():
            response = super().update(request, *args, **kwargs)
            session = getattr(request, 'client_login_session', None)
            if session is not None:
                from authentication.services.client_login_session import client_login_session_data
                session.refresh_from_db()
                response.data['client_login_session'] = client_login_session_data(session)
            return response
