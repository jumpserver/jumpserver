# ~*~ coding: utf-8 ~*~
#

import logging

from rest_framework import generics, mixins, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import UserSerializer, UserGroupSerializer
from .models import User, UserGroup


logger = logging.getLogger('jumpserver.users.api')


class UserListAddApi(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    # permission_classes = (
    #     permissions.DenyAll,
    # )


class UserDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def put(self, request, *args, **kwargs):
        logger.debug(request.META)
        return super(UserDetailDeleteUpdateApi, self).put(request, *args, **kwargs)

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

