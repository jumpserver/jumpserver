from assets.models import Web
from .common import AssetSerializer

__all__ = ['WebSerializer']


class WebSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Web
        fields = AssetSerializer.Meta.fields + [
            'autofill', 'username_selector',
            'password_selector', 'submit_selector',
            'script'
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': 'URL'
            },
            'username_selector': {
                'default': 'name=username'
            },
            'password_selector': {
                'default': 'name=password'
            },
            'submit_selector': {
                'default': 'id=login_button',
            },
            'script': {
                'default': [],
            }
        }

    def to_internal_value(self, data):
        data = data.copy()
        if data.get('script') in ("", None):
            data.pop('script', None)
        return super().to_internal_value(data)
