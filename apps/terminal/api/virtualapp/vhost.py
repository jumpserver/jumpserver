from django.core.cache import cache
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from common.api import JMSBulkModelViewSet
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_builtin_org
from terminal.models import VirtualHost
from terminal.serializers import (
    VirtualHostSerializer, VirtualHostContainerSerializer
)

__all__ = ['VirtualHostViewSet', ]


class VirtualHostViewSet(JMSBulkModelViewSet):
    serializer_class = VirtualHostSerializer
    queryset = VirtualHost.objects.all()
    search_fields = ['name', 'hostname', ]
    rbac_perms = {
        'containers': 'terminal.view_virtualhost',
        'status': 'terminal.view_virtualhost',
    }

    cache_status_key_prefix = 'virtual_host_{}_status'

    def dispatch(self, request, *args, **kwargs):
        with tmp_to_builtin_org(system=1):
            return super().dispatch(request, *args, **kwargs)

    def get_permissions(self):
        if self.action == 'create':
            return [IsServiceAccount()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        request_terminal = getattr(request.user, 'terminal', None)
        if not request_terminal:
            raise ValidationError('Request user has no terminal')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        data = dict(**validated_data)
        data['terminal'] = request_terminal
        data['id'] = request.user.id
        instance = VirtualHost.objects.create(**data)
        serializer = self.get_serializer(instance=instance)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['get'], serializer_class=VirtualHostContainerSerializer)
    def containers(self, request, *args, **kwargs):
        instance = self.get_object()
        key = self.cache_status_key_prefix.format(instance.id)
        data = cache.get(key)
        if not data:
            data = []
        page = self.paginate_queryset(data)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], serializer_class=VirtualHostContainerSerializer)
    def status(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        key = self.cache_status_key_prefix.format(instance.id)
        cache.set(key, validated_data, 60 * 3)
        return Response({'msg': 'ok'})
