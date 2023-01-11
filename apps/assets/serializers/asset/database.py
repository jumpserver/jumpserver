from assets.models import Database
from .common import AssetSerializer
from ..gateway import GatewayWithAccountSecretSerializer

__all__ = ['DatabaseSerializer', 'DatabaseWithGatewaySerializer']


class DatabaseSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Database
        extra_fields = [
            'db_name', 'use_ssl', 'ca_cert', 'client_cert',
            'client_key', 'allow_invalid_cert'
        ]
        fields = AssetSerializer.Meta.fields + extra_fields


class DatabaseWithGatewaySerializer(DatabaseSerializer):
    gateway = GatewayWithAccountSecretSerializer()

    class Meta(DatabaseSerializer.Meta):
        fields = DatabaseSerializer.Meta.fields + ['gateway']
