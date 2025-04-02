from assets.models import AD, Asset
from assets.serializers import ADSerializer

from .asset import AssetViewSet

__all__ = ['ADViewSet']


class ADViewSet(AssetViewSet):
    model = AD
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = ADSerializer
        return serializer_classes
