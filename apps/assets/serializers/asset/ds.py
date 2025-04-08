from django.utils.translation import gettext_lazy as _

from assets.models import DirectoryService
from .common import AssetSerializer

__all__ = ['DSSerializer']


class DSSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = DirectoryService
        fields = AssetSerializer.Meta.fields + [
            'domain_name',
        ]
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'domain_name': {
                'help_text': _('The domain name of the active directory or other directory service'),
                'label': _('Domain name')
            }
        }
