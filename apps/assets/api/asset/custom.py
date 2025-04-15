from assets.models import Custom, Asset
from assets.serializers import CustomSerializer

from .asset import BaseAssetViewSet

__all__ = ['CustomViewSet']


class CustomViewSet(BaseAssetViewSet):
    model = Custom
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = CustomSerializer
        return serializer_classes
