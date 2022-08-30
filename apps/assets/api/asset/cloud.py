from assets.models import Cloud
from assets.serializers import CloudSerializer

from .asset import AssetViewSet

__all__ = ['CloudViewSet']


class CloudViewSet(AssetViewSet):
    model = Cloud

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = CloudSerializer
        return serializer_classes
