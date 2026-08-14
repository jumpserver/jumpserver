from django.utils.translation import gettext_lazy as _

from assets.models import Host
from .common import AssetSerializer
from .info.gathered import HostGatheredInfoSerializer
from .template_definition import host_import_template

__all__ = ['HostSerializer']


class HostSerializer(AssetSerializer):
    gathered_info = HostGatheredInfoSerializer(required=False, read_only=True, label=_("Gathered info"))

    class Meta(AssetSerializer.Meta):
        model = Host
        fields = AssetSerializer.Meta.fields + ['gathered_info']
        import_template = host_import_template
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': _("IP/Host")
            },
        }
