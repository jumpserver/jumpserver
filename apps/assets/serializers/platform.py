from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from assets.models import Platform
from assets.const import AllTypes
from .mixin import CategoryDisplayMixin

__all__ = ['PlatformSerializer']


class PlatformSerializer(CategoryDisplayMixin, serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True, label=_('Meta'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO 修复 drf SlugField RegexValidator bug，之后记得删除
        validators = self.fields['name'].validators
        if isinstance(validators[-1], RegexValidator):
            validators.pop()

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'meta', 'comment', 'charset',
            'category', 'category_display', 'type', 'type_display',
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


