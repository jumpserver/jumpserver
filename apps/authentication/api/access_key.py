# -*- coding: utf-8 -*-
#

from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from common.permissions import UserConfirmation
from rbac.permissions import RBACPermission
from ..const import ConfirmType
from ..serializers import AccessKeySerializer


class AccessKeyViewSet(ModelViewSet):
    serializer_class = AccessKeySerializer
    search_fields = ['^id', '^secret']
    permission_classes = [RBACPermission]

    def get_queryset(self):
        return self.request.user.access_keys.all()

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False) or getattr(self, 'raw_action', '') == 'metadata':
            return super().get_permissions()

        if self.action == 'create':
            self.permission_classes = [
                RBACPermission, UserConfirmation.require(ConfirmType.PASSWORD)
            ]
        return super().get_permissions()

    def perform_create(self, serializer):
        user = self.request.user
        key = user.create_access_key()
        return key

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        key = self.perform_create(serializer)
        return Response({'secret': key.secret, 'id': key.id}, status=201)
