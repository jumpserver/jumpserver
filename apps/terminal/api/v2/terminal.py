# -*- coding: utf-8 -*-
#
from rest_framework import viewsets

from common.permissions import IsSuperUser, WithBootstrapToken
from ...models import Terminal
from ...serializers import v2 as serializers

__all__ = ['TerminalViewSet', 'TerminalRegistrationViewSet']


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    permission_classes = [IsSuperUser]


class TerminalRegistrationViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalRegistrationSerializer
    permission_classes = [WithBootstrapToken]
    http_method_names = ['post']
