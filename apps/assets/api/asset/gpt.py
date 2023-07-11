from assets.models import GPT, Asset
from assets.serializers import GPTSerializer

from .asset import AssetViewSet

__all__ = ['GPTViewSet']


class GPTViewSet(AssetViewSet):
    model = GPT
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = GPTSerializer
        return serializer_classes
