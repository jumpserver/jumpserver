# -*- coding: utf-8 -*-
#

from rest_framework import generics
from rest_framework_bulk import BulkModelViewSet

from ..serializers import UserGroupSerializer, \
    UserGroupUpdateMemeberSerializer
from ..models import UserGroup
from common.permissions import IsOrgAdmin
from common.mixins import IDInFilterMixin


__all__ = ['UserGroupViewSet', 'UserGroupUpdateUserApi']


class UserGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsOrgAdmin,)


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupUpdateMemeberSerializer
    permission_classes = (IsOrgAdmin,)
