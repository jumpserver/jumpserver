# -*- coding: utf-8 -*-
#
from rest_framework import viewsets, generics
from rest_framework import status
from rest_framework.response import Response

from common.permissions import IsSuperUser, WithBootstrapToken


from ..models import Terminal
from .. import serializers_v2 as serializers

__all__ = ['TerminalViewSet', 'TerminalRegistrationApi']


class TerminalViewSet(viewsets.ModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    permission_classes = [IsSuperUser]


class TerminalRegistrationApi(generics.CreateAPIView):
    serializer_class = serializers.TerminalRegistrationSerializer
    permission_classes = [WithBootstrapToken]
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        data = {k: v for k, v in request.data.items()}
        serializer = serializers.TerminalSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        terminal = serializer.save()
        sa_serializer = serializer.sa_serializer_class(instance=terminal.user)
        data['service_account'] = sa_serializer.data
        return Response(data, status=status.HTTP_201_CREATED)

