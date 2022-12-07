# -*- coding: utf-8 -*-
#

from rest_framework import generics
from rest_framework.views import Response

from common.permissions import IsValidUser
from common.utils import get_request_os
from terminal import serializers
from terminal.connect_methods import ConnectMethodUtil

__all__ = ['ConnectMethodListApi']


class ConnectMethodListApi(generics.ListAPIView):
    serializer_class = serializers.ConnectMethodSerializer
    permission_classes = [IsValidUser]

    def get_queryset(self):
        os = get_request_os(self.request)
        return ConnectMethodUtil.get_protocols_connect_methods(os)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)
