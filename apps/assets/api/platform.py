
from common.drf.api import JMSModelViewSet
from common.drf.serializers import GroupedChoiceSerializer
from assets.models import Platform
from assets.serializers import PlatformSerializer


__all__ = ['AssetPlatformViewSet']


class AssetPlatformViewSet(JMSModelViewSet):
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

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)
