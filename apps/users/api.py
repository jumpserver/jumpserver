# ~*~ coding: utf-8 ~*~
#

from rest_framework import viewsets

from .serializers import UserSerializer
from .models import User, UserGroup, Role


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
