
from assets.models import Device
from .common import AssetSerializer
from .template_definition import device_import_template

__all__ = ['DeviceSerializer']


class DeviceSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Device
        import_template = device_import_template
