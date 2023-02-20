# -*- coding: utf-8 -*-
#
import logging
from django.db.models import Q
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import generics
from rest_framework import status
from rest_framework.views import APIView, Response
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from common.api import JMSBulkModelViewSet
from common.exceptions import JMSException
from common.permissions import WithBootstrapToken
from terminal import serializers
from terminal.models import Terminal

__all__ = [
    'TerminalViewSet', 'TerminalConfig',
    'TerminalRegistrationApi',
]
logger = logging.getLogger(__file__)


class TerminalFilterSet(BaseFilterSet):
    name = filters.CharFilter(field_name='name', lookup_expr='icontains')
    remote_addr = filters.CharFilter(field_name='remote_addr', lookup_expr='icontains')

    class Meta:
        model = Terminal
        fields = ['name', 'remote_addr', 'type']

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        search = self.request.query_params.get('search')
        if not search:
            return queryset
        q = Q(name__icontains=search) | Q(remote_addr__icontains=search)
        queryset = queryset.filter(q)
        return queryset


class TerminalViewSet(JMSBulkModelViewSet):
    queryset = Terminal.objects.filter(is_deleted=False)
    serializer_class = serializers.TerminalSerializer
    filterset_class = TerminalFilterSet
    custom_filter_fields = ['load']

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
        s = self.request.query_params.get('load')
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

