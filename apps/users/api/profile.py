# ~*~ coding: utf-8 ~*~
import uuid

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from authentication.models import ConnectionToken
from authentication.permissions import IsValidUserOrConnectionToken
from common.utils import get_object_or_none
from orgs.utils import tmp_to_root_org
from users.notifications import (
    ResetPasswordMsg, ResetPasswordSuccessMsg, ResetSSHKeyMsg,
    ResetPublicKeySuccessMsg,
)
from .mixins import UserQuerysetMixin
from .. import serializers
from ..models import User

__all__ = [
    'UserResetPasswordApi', 'UserResetPKApi',
    'UserProfileApi', 'UserPasswordApi',
    'UserPublicKeyApi'
]


class UserResetPasswordApi(UserQuerysetMixin, generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password stuff.
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        ResetPasswordMsg(user).publish_async()


class UserResetPKApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = None
        user.save()
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

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        ResetPasswordSuccessMsg(self.request.user, request).publish_async()
        return resp


class UserPublicKeyApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePublicKeySerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        super().perform_update(serializer)
        ResetPublicKeySuccessMsg(self.get_object(), self.request).publish_async()
