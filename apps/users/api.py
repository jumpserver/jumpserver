# ~*~ coding: utf-8 ~*~
#

from rest_framework import generics
from rest_framework import mixins

from .serializers import UserSerializer
from .models import User, UserGroup


class UserListApi(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
