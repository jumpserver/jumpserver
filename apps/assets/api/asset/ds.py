from assets.models import DirectoryService, Asset
from assets.serializers import DSSerializer

from .asset import AssetViewSet

__all__ = ['DSViewSet']


class DSViewSet(AssetViewSet):
    model = DirectoryService
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = DSSerializer
        return serializer_classes
