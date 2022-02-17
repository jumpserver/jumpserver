# ~*~ coding: utf-8 ~*~
import uuid

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from users.notifications import (
    ResetPasswordMsg, ResetPasswordSuccessMsg, ResetSSHKeyMsg,
    ResetPublicKeySuccessMsg,
)

from .. import serializers
from ..models import User
from .mixins import UserQuerysetMixin

__all__ = [
    'UserResetPasswordApi', 'UserResetPKApi',
    'UserProfileApi', 'UserPasswordApi',
    'UserSecretKeyApi', 'UserPublicKeyApi'
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
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserProfileSerializer

    def get_object(self):
        return self.request.user


class UserPasswordApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePasswordSerializer

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        resp = super().update(request, *args, **kwargs)
        ResetPasswordSuccessMsg(self.request.user, request).publish_async()
        return resp


class UserSecretKeyApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdateSecretKeySerializer

    def get_object(self):
        return self.request.user


class UserPublicKeyApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePublicKeySerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        super().perform_update(serializer)
        ResetPublicKeySuccessMsg(self.get_object(), self.request).publish_async()
