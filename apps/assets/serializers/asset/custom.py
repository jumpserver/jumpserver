from assets.models import Custom
from .common import AssetSerializer

__all__ = ['CustomSerializer']


class CustomSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Custom
