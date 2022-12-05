# -*- coding: utf-8 -*-
#
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework import status
from rest_framework.views import APIView, Response

from common.drf.api import JMSBulkModelViewSet
from common.exceptions import JMSException
from common.permissions import IsValidUser
from common.permissions import WithBootstrapToken
from common.utils import get_request_os
from terminal import serializers
from terminal.const import TerminalType
from terminal.models import Terminal

__all__ = [
    'TerminalViewSet', 'TerminalConfig',
    'TerminalRegistrationApi', 'ConnectMethodListApi'
]
logger = logging.getLogger(__file__)


class TerminalViewSet(JMSBulkModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    filterset_fields = ['name', 'remote_addr', 'type']
    custom_filter_fields = ['status']

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.get_online_session_count() > 0:
            raise JMSException(
                code='have_online_session',
                detail=_('Have online sessions')
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        s = self.request.query_params.get('status')
        if not s:
            return queryset
        filtered_queryset_id = [str(q.id) for q in queryset if q.load == s]
        queryset = queryset.filter(id__in=filtered_queryset_id)
        return queryset


class TerminalConfig(APIView):
    rbac_perms = {
        'GET': 'terminal.view_terminalconfig'
    }

    def get(self, request):
        config = request.user.terminal.config
        return Response(config, status=200)


class TerminalRegistrationApi(generics.CreateAPIView):
    serializer_class = serializers.TerminalRegistrationSerializer
    permission_classes = [WithBootstrapToken]
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        if not settings.SECURITY_SERVICE_ACCOUNT_REGISTRATION:
            data = {"error": "service account registration disabled"}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().create(request, *args, **kwargs)


class ConnectMethodListApi(generics.ListAPIView):
    serializer_class = serializers.ConnectMethodSerializer
    permission_classes = [IsValidUser]

    def get_queryset(self):
        os = get_request_os(self.request)
        return TerminalType.get_protocols_connect_methods(os)

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        return Response(queryset)
