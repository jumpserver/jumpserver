
from assets.serializers import DeviceSerializer
from assets.models import Device
from .asset import AssetViewSet

__all__ = ['DeviceViewSet']


class DeviceViewSet(AssetViewSet):
    model = Device

    def get_serializer_classes(self):
        serializer_classes = super().get_serializer_classes()
        serializer_classes['default'] = DeviceSerializer
        return serializer_classes
