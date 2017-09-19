# ~*~ coding: utf-8 ~*~
#

from rest_framework import viewsets
from users.permissions import IsValidUser
from .models import ApplyPermission
from . import serializers

class ApplyPermissionViewSet(viewsets.ModelViewSet):
    queryset = ApplyPermission.objects.all()
    serializer_class = serializers.ApplyPermissionSerializer
    permission_classes = (IsValidUser,)

