from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from assets.models import Custom, Platform, Asset
from common.const import UUID_PATTERN
from common.serializers import create_serializer_class
from common.serializers.common import DictSerializer, MethodSerializer
from .common import AssetSerializer

__all__ = ['CustomSerializer']


class CustomSerializer(AssetSerializer):
    custom_info = MethodSerializer(label=_('Custom info'), required=False, allow_null=True)

    class Meta(AssetSerializer.Meta):
        model = Custom
        fields = AssetSerializer.Meta.fields + ['custom_info']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self, 'initial_data') and not self.initial_data.get('custom_info'):
            self.initial_data['custom_info'] = {}

    def get_custom_info_serializer(self):
        request = self.context.get('request')
        default_field = DictSerializer()

        if not request:
            return default_field

        if self.instance and isinstance(self.instance, (QuerySet, list)):
            return default_field

        if not self.instance and UUID_PATTERN.findall(request.path):
            pk = UUID_PATTERN.findall(request.path)[0]
            self.instance = Asset.objects.filter(id=pk).first()

        platform = None
        if self.instance:
            platform = self.instance.platform
        elif request.query_params.get('platform'):
            platform_id = request.query_params.get('platform')
            platform_id = int(platform_id) if platform_id.isdigit() else 0
            platform = Platform.objects.filter(id=platform_id).first()

        if not platform:
            return default_field
        custom_fields = platform.custom_fields
        if not custom_fields:
            return default_field
        name = platform.name.title() + 'CustomSerializer'
        return create_serializer_class(name, custom_fields)()
