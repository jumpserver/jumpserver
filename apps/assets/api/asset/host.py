from assets.models import Host, Asset
from assets.serializers import HostSerializer
from .asset import AssetViewSet

__all__ = ['HostViewSet']


class HostViewSet(AssetViewSet):
    model = Host
    perm_model = Asset

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = HostSerializer
        return serializer_classes
