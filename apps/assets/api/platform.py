from typing import Callable

from rest_framework.generics import RetrieveUpdateAPIView

from assets.const import AllTypes
from assets.models import Platform
from assets.serializers import PlatformSerializer, PlatformAutomationBySSHCommandsSerializer
from common.api import JMSModelViewSet
from common.serializers import GroupedChoiceSerializer

__all__ = ['AssetPlatformViewSet', 'PlatformAutomationCommands']


class PlatformPermissionMixin:
    permission_denied: Callable

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)


class AssetPlatformViewSet(JMSModelViewSet, PlatformPermissionMixin):
    queryset = Platform.objects.all()
    serializer_classes = {
        'default': PlatformSerializer,
        'categories': GroupedChoiceSerializer
    }
    filterset_fields = ['name', 'category', 'type']
    search_fields = ['name']
    rbac_perms = {
        'categories': 'assets.view_platform',
        'type_constraints': 'assets.view_platform',
        'ops_methods': 'assets.view_platform'
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(type__in=AllTypes.get_types())
        return queryset

    def get_object(self):
        pk = self.kwargs.get('pk', '')
        if pk.isnumeric():
            return super().get_object()
        return self.get_queryset().get(name=pk)


class PlatformAutomationCommands(RetrieveUpdateAPIView, PlatformPermissionMixin):
    queryset = Platform.objects.filter(internal=False)
    serializer_classes = {
        'default': PlatformAutomationBySSHCommandsSerializer,
        'change_secret_by_ssh': PlatformAutomationBySSHCommandsSerializer
    }
    rbac_perms = {
        'GET': 'assets.view_platform',
        'PUT': 'assets.change_platform',
        'PATCH': 'assets.change_platform',
    }

    def get_serializer_class(self):
        method = self.request.query_params.get('method', 'default')
        serializer = self.serializer_classes.get(method)
        return serializer or self.serializer_classes['default']
