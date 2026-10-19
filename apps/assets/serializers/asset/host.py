from django.utils.translation import gettext_lazy as _

from assets.models import Host
from assets.validators import validate_ip_or_hostname
from .common import AssetSerializer
from .info.gathered import HostGatheredInfoSerializer

__all__ = ['HostSerializer']


class HostSerializer(AssetSerializer):
    gathered_info = HostGatheredInfoSerializer(required=False, read_only=True, label=_("Gathered info"))

    def validate_address(self, value):
        value = super().validate_address(value)
        validate_ip_or_hostname(value)
        return value

    class Meta(AssetSerializer.Meta):
        model = Host
        fields = AssetSerializer.Meta.fields + ['gathered_info']
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': _("IP/Host")
            },
        }
