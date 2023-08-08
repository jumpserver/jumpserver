# -*- coding: utf-8 -*-
#

from rest_framework.viewsets import ModelViewSet

from rbac.permissions import RBACPermission
from ..serializers import AccessKeySerializer


class AccessKeyViewSet(ModelViewSet):
    serializer_class = AccessKeySerializer
    search_fields = ['^id', '^secret']
    permission_classes = [RBACPermission]

    def get_queryset(self):
        return self.request.user.access_keys.all()

    def perform_create(self, serializer):
        user = self.request.user
        user.create_access_key()
