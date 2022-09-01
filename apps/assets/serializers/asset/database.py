
from assets.models import Database
from .common import AssetSerializer

__all__ = ['DatabaseSerializer']


class DatabaseSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Database
        fields = AssetSerializer.Meta.fields + ['db_name']
