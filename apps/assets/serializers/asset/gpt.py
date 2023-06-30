from assets.models import GPT
from .common import AssetSerializer

__all__ = ['GPTSerializer']


class GPTSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = GPT
        fields = AssetSerializer.Meta.fields + [
            'proxy',
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
        }
