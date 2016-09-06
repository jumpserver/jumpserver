# ~*~ coding: utf-8 ~*~
#

import logging

from rest_framework import generics

from .serializers import UserSerializer, UserGroupSerializer, UserAttributeSerializer
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
