from assets.models import Cloud
from .common import AssetSerializer

__all__ = ['CloudSerializer']


class CloudSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Cloud
        fields = AssetSerializer.Meta.fields
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': 'URL'
            }
        }
