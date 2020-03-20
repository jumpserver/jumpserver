# ~*~ coding: utf-8 ~*~
import uuid

from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from common.permissions import (
    IsCurrentUserOrReadOnly
)
from .. import serializers
from ..models import User
from .mixins import UserQuerysetMixin

__all__ = [
    'UserResetPasswordApi', 'UserResetPKApi',
    'UserProfileApi', 'UserUpdatePKApi',
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


class UserProfileApi(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = serializers.UserSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        age = request.session.get_expiry_age()
        request.session.set_expiry(age)
        return super().retrieve(request, *args, **kwargs)
