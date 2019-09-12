# -*- coding: utf-8 -*-
#

from rest_framework.viewsets import ModelViewSet

from common.permissions import IsValidUser
from .. import serializers


class AccessKeyViewSet(ModelViewSet):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AccessKeySerializer
    search_fields = ['^id', '^secret']

    def get_queryset(self):
        return self.request.user.access_keys.all()

    def perform_create(self, serializer):
        user = self.request.user
        user.create_access_key()
