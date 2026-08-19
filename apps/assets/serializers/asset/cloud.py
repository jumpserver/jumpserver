from assets.models import Cloud
from .common import AssetSerializer
from .template_definition import cloud_import_template

__all__ = ['CloudSerializer']


class CloudSerializer(AssetSerializer):
    class Meta(AssetSerializer.Meta):
        model = Cloud
        fields = AssetSerializer.Meta.fields
        import_template = cloud_import_template
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'address': {
                'label': 'URL'
            }
        }
