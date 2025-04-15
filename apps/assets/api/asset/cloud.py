from assets.models import Cloud, Asset
from assets.serializers import CloudSerializer

from .asset import BaseAssetViewSet

__all__ = ['CloudViewSet']


class CloudViewSet(BaseAssetViewSet):
    model = Cloud
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = CloudSerializer
        return serializer_classes
