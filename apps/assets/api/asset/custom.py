from assets.models import Custom, Asset
from assets.serializers import WebSerializer

from .asset import AssetViewSet

__all__ = ['CustomViewSet']


class CustomViewSet(AssetViewSet):
    model = Custom
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = WebSerializer
        return serializer_classes
