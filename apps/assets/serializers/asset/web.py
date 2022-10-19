
from assets.models import Web
from .common import AssetSerializer

__all__ = ['WebSerializer']


class WebSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Web
        fields = AssetSerializer.Meta.fields + [
            'autofill', 'username_selector',
            'password_selector', 'submit_selector'
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': 'URL'
            },
            'username_selector': {
                'default': 'input[type=text]'
            },
            'password_selector': {
                'default': 'input[type=password]'
            },
            'submit_selector': {
                'default': 'button[type=submit]',
            }
        }
