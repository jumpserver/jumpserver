# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import IsAppUser, IsSuperUser
from .models import Terminal
from .serializers import TerminalSerializer


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = TerminalSerializer
    permission_classes = (IsSuperUser,)

    def get_object(self):
        if self.request.user.is_app():
            return self.request.user.terminal
        else:
            return super().get_object()

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.is_accepted = True
        instance.user = self.request.user
        instance.save()

    def get_permissions(self):
        if self.action in ["create", "retrieve"]:
            self.permission_classes = (IsAppUser,)
        return super().get_permissions()
