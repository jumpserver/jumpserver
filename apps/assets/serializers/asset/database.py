from assets.models import Database
from .common import AssetSerializer
from ..gateway import GatewayWithAccountSecretSerializer

__all__ = ['DatabaseSerializer', 'DatabaseWithGatewaySerializer']


class DatabaseSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Database
        fields = AssetSerializer.Meta.fields + ['db_name']


class DatabaseWithGatewaySerializer(DatabaseSerializer):
    gateway = GatewayWithAccountSecretSerializer()

    class Meta(DatabaseSerializer.Meta):
        fields = DatabaseSerializer.Meta.fields + ['gateway']
