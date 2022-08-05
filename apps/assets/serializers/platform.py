from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from assets.models import Platform
from .mixin import CategoryDisplayMixin

__all__ = ['PlatformSerializer']


class PlatformSerializer(CategoryDisplayMixin, serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True, label=_('Meta'))
    protocols_default = serializers.ListField(label=_('Protocols'), required=False)
    type_limits = serializers.ReadOnlyField(required=False, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO 修复 drf SlugField RegexValidator bug，之后记得删除
        validators = self.fields['name'].validators
        if isinstance(validators[-1], RegexValidator):
            validators.pop()
        # self.set_platform_meta()

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'meta', 'comment', 'charset',
            'category', 'category_display',
            'type', 'type_display',
            'type_limits',
        ]
        fields_fk = [
            'domain_enabled', 'domain_default',
            'protocols_enabled', 'protocols_default',
            'admin_user_enabled', 'admin_user_default',
        ]
        fields = fields_small + fields_fk
        read_only_fields = [
            'category_display', 'type_display',
        ]


