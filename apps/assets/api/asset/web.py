from assets.models import Web
from assets.serializers import WebSerializer

from .asset import AssetViewSet

__all__ = ['WebViewSet']


class WebViewSet(AssetViewSet):
    model = Web

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = WebSerializer
        return serializer_classes
