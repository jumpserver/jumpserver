# -*- coding: utf-8 -*-
#

from rest_framework.viewsets import ModelViewSet
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser
from .. import serializers


class AccessKeyViewSet(ModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AccessKeySerializer
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return self.request.user.access_keys.all()

    def perform_create(self, serializer):
        user = self.request.user
        user.create_access_key()
