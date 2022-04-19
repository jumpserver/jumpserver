# -*- coding: utf-8 -*-
#

from rest_framework.viewsets import ModelViewSet
from .. import serializers
from rbac.permissions import RBACPermission


class AccessKeyViewSet(ModelViewSet):
    serializer_class = serializers.AccessKeySerializer
    search_fields = ['^id', '^secret']
    permission_classes = [RBACPermission]

    def get_queryset(self):
        return self.request.user.access_keys.all()

    def perform_create(self, serializer):
        user = self.request.user
        user.create_access_key()
