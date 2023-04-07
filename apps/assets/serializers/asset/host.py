from django.utils.translation import gettext_lazy as _

from assets.models import Host
from .common import AssetSerializer

__all__ = ['HostSerializer']


class HostSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Host
        fields = AssetSerializer.Meta.fields
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': _("IP/Host")
            },
        }
