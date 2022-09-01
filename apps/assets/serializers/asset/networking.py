
from assets.models import Networking
from .common import AssetSerializer

__all__ = ['NetworkingSerializer']


class NetworkingSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Networking
