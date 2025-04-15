from assets.models import Web, Asset
from assets.serializers import WebSerializer

from .asset import BaseAssetViewSet

__all__ = ['WebViewSet']


class WebViewSet(BaseAssetViewSet):
    model = Web
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = WebSerializer
        return serializer_classes
