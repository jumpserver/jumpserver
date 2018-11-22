# -*- coding: utf-8 -*-
#
from rest_framework import viewsets
from rest_condition import Or, And

from common.permissions import IsAppUser, IsSuperUser
from common.utils import get_request_ip
from ...models import Terminal
from ...serializers import v2 as serializers

__all__ = ['TerminalViewSet']


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    permission_classes = [IsSuperUser]
    permission_classes_create_list = [Or(And(*permission_classes), IsAppUser)]

    def get_queryset(self):
        if self.request.user.is_app:
            if hasattr(self.request.user, 'terminal'):
                return [self.request.user.terminal]
            return []
        return super().get_queryset()

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.is_accepted = True
        instance.user = self.request.user
        instance.remote_addr = get_request_ip(self.request)
        instance.save()

    def get_permissions(self):
        if self.action in ["create", "list"]:
            self.permission_classes = self.permission_classes_create_list
        return super().get_permissions()
