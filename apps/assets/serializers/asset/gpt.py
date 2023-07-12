from django.utils.translation import gettext_lazy as _

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
            'proxy': {
                'help_text': _(
                    'If the server cannot directly connect to the API address, '
                    'you need set up an HTTP proxy. '
                    'e.g. http(s)://host:port'
                ),
                'label': _('HTTP proxy')}
        }
