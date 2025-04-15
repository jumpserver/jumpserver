from assets.models import Database, Asset
from assets.serializers import DatabaseSerializer

from .asset import BaseAssetViewSet

__all__ = ['DatabaseViewSet']


class DatabaseViewSet(BaseAssetViewSet):
    model = Database
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = DatabaseSerializer
        return serializer_classes
