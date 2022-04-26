from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from assets.models import Platform

__all__ = ['PlatformSerializer']


class PlatformSerializer(serializers.ModelSerializer):
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_("Category display"))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_("Type display"))
    meta = serializers.DictField(required=False, allow_null=True, label=_('Meta'))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # TODO 修复 drf SlugField RegexValidator bug，之后记得删除
        validators = self.fields['name'].validators
        if isinstance(validators[-1], RegexValidator):
            validators.pop()

    class Meta:
        model = Platform
        fields = [
            'id', 'name', 'category', 'category_display',
            'type', 'type_display', 'charset',
            'internal', 'meta', 'comment'
        ]
