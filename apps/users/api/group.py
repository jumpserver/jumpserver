# -*- coding: utf-8 -*-
#

from rest_framework import generics
from rest_framework_bulk import BulkModelViewSet
from rest_framework.pagination import LimitOffsetPagination

from ..serializers import (
    UserGroupSerializer,
    UserGroupListSerializer,
    UserGroupUpdateMemberSerializer,
)
from ..models import UserGroup
from common.permissions import IsOrgAdmin
from common.mixins import IDInCacheFilterMixin


__all__ = ['UserGroupViewSet', 'UserGroupUpdateUserApi']


class UserGroupViewSet(IDInCacheFilterMixin, BulkModelViewSet):
    filter_fields = ("name",)
    search_fields = filter_fields
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsOrgAdmin,)
    pagination_class = LimitOffsetPagination

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve') and \
                self.request.query_params.get("display"):
            return UserGroupListSerializer
        return self.serializer_class


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupUpdateMemberSerializer
    permission_classes = (IsOrgAdmin,)
