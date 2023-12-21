from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.api import JMSBulkModelViewSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import AppProvider
from terminal.serializers import (
    AppProviderSerializer, AppProviderContainerSerializer
)

__all__ = ['AppProviderViewSet', ]


class AppProviderViewSet(JMSBulkModelViewSet):
    serializer_class = AppProviderSerializer
    queryset = AppProvider.objects.all()
    search_fields = ['name', 'hostname', ]
    rbac_perms = {
        'containers': 'terminal.view_appprovider',
        'status': 'terminal.view_appprovider',
    }

    cache_status_key_prefix = 'virtual_host_{}_status'

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'create':
            return [IsServiceAccount()]
        return super().get_permissions()

    def perform_create(self, serializer):
        request_terminal = getattr(self.request.user, 'terminal', None)
        if not request_terminal:
            raise ValidationError('Request user has no terminal')
        data = dict()
        data['terminal'] = request_terminal
        data['id'] = self.request.user.id
        serializer.save(**data)

    @action(detail=True, methods=['get'], serializer_class=AppProviderContainerSerializer)
    def containers(self, request, *args, **kwargs):
        instance = self.get_object()
        key = self.cache_status_key_prefix.format(instance.id)
        data = cache.get(key)
        if not data:
            data = []
        return self.get_paginated_response_from_queryset(data)

    @action(detail=True, methods=['post'], serializer_class=AppProviderContainerSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        key = self.cache_status_key_prefix.format(instance.id)
        cache.set(key, validated_data, 60 * 3)
        return Response({'msg': 'ok'})
