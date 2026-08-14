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
        # 目录服务无专门导入模板，避免继承通用 host 模板
        import_template = None
        extra_kwargs = {
            **AssetSerializer.Meta.extra_kwargs,
            'domain_name': {
                'help_text': _('The domain part used by the directory service (e.g., AD) and appended to '
                               'the username during login, such as example.com in user@example.com.'),
                'label': _('Domain name')
            }
        }
