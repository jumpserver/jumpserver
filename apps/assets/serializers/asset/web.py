
from assets.models import Web
from .common import AssetSerializer

__all__ = ['WebSerializer']


class WebSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Web
        fields = AssetSerializer.Meta.fields + [
            'url', 'autofill', 'username_selector',
            'password_selector', 'submit_selector'
        ]
