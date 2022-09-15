from assets.models import Device
from .common import AssetSerializer

__all__ = ['NetworkingSerializer']


class NetworkingSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Device
