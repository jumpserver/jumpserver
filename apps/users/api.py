# ~*~ coding: utf-8 ~*~
#

import logging

from rest_framework import generics

from .serializers import UserSerializer, UserGroupSerializer, UserAttributeSerializer, UserGroupEditSerializer
from .serializers import UserPKUpdateSerializer
from .models import User, UserGroup


logger = logging.getLogger('jumpserver.users.api')


class UserListAddApi(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def delete(self, request, *args, **kwargs):
        print(self.request.data)
        return super(UserDetailDeleteUpdateApi, self).delete(request, *args, **kwargs)

    # def get(self, request, *args, **kwargs):
    #     print("hello world")
    #     print(request.user)
    #     return super(UserDetailDeleteUpdateApi, self).get(request, *args, **kwargs)


class UserGroupListAddApi(generics.ListCreateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserGroupDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserAttributeApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserAttributeSerializer


class UserGroupEditApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserGroupEditSerializer


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserGroupEditSerializer

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password staff.
        user = self.get_object()
        from .utils import send_reset_password_mail
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserPKUpdateSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.private_key = serializer.validated_data['_private_key']
        user.save()
