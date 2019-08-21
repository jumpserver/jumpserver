# -*- coding: utf-8 -*-
#

from rest_framework import generics

from ..serializers import (
    UserGroupSerializer,
    UserGroupListSerializer,
    UserGroupUpdateMemberSerializer,
)
from ..models import UserGroup
from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin


__all__ = ['UserGroupViewSet', 'UserGroupUpdateUserApi']


class UserGroupViewSet(OrgBulkModelViewSet):
    filter_fields = ("name",)
    search_fields = filter_fields
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve') and \
                self.request.query_params.get("display"):
            return UserGroupListSerializer
        return self.serializer_class


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupUpdateMemberSerializer
    permission_classes = (IsOrgAdmin,)
