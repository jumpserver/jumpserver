# ~*~ coding: utf-8 ~*~
import uuid

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from django.conf import settings

from common.permissions import (
    IsCurrentUserOrReadOnly
)
from .. import serializers
from ..models import User
from ..utils import send_reset_password_success_mail
from .mixins import UserQuerysetMixin

__all__ = [
    'UserResetPasswordApi', 'UserResetPKApi',
    'UserProfileApi', 'UserUpdatePKApi',
    'UserPasswordApi', 'UserPublicKeyApi'
]


class UserResetPasswordApi(UserQuerysetMixin, generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password stuff.
        from ..utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.UserSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        from ..utils import send_reset_ssh_key_mail
        user = self.get_object()
        user.public_key = None
        user.save()
        send_reset_ssh_key_mail(user)


# 废弃
class UserUpdatePKApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.UserPKUpdateSerializer
    permission_classes = (IsCurrentUserOrReadOnly,)

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = serializer.validated_data['public_key']
        user.save()


class UserProfileApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserProfileSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        if not settings.SESSION_EXPIRE_AT_BROWSER_CLOSE:
            age = request.session.get_expiry_age()
            request.session.set_expiry(age)
        return super().retrieve(request, *args, **kwargs)


class UserPasswordApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePasswordSerializer

    def get_object(self):
        return self.request.user


class UserPublicKeyApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserUpdatePublicKeySerializer

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        super().perform_update(serializer)
        send_reset_password_success_mail(self.request, self.get_object())
