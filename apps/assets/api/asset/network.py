
from assets.serializers import HostSerializer
from assets.models import Networking
from .asset import AssetViewSet

__all__ = ['NetworkViewSet']


class NetworkViewSet(AssetViewSet):
    model = Networking

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = HostSerializer
        return serializer_classes
