# ~*~ coding: utf-8 ~*~
#

import logging

from rest_framework import generics, mixins, status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import UserSerializer, UserGroupSerializer, UserActiveSerializer
from .models import User, UserGroup


logger = logging.getLogger('jumpserver.users.api')


class UserListAddApi(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserActiveApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserActiveSerializer

    # def put(self, request, *args, **kwargs):
    #     for k, v in request.META.items():
    #         logger.debug("%s --> %s" % (k, v))
    #     return super(UserActiveApi, self).put(request, *args, **kwargs)


class UserGroupListAddApi(generics.ListCreateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserGroupDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer

