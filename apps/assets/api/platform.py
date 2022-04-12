from rest_framework.viewsets import ModelViewSet

from assets.models import Platform
from assets.serializers import PlatformSerializer


__all__ = ['AssetPlatformViewSet']


class AssetPlatformViewSet(ModelViewSet):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    filterset_fields = ['name']
    search_fields = ['name']

    def check_object_permissions(self, request, obj):
        if request.method.lower() in ['delete', 'put', 'patch'] and obj.internal:
            self.permission_denied(
                request, message={"detail": "Internal platform"}
            )
        return super().check_object_permissions(request, obj)
