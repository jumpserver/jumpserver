from rest_framework import serializers
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

from assets.models import Platform
from .mixin import CategoryDisplayMixin

__all__ = ['PlatformSerializer']


class PlatformProtocolsSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255, required=True)
    port = serializers.IntegerField(max_value=65535, min_value=1, required=True)


class PlatformSerializer(CategoryDisplayMixin, serializers.ModelSerializer):
    meta = serializers.DictField(required=False, allow_null=True, label=_('Meta'))
    protocols_default = PlatformProtocolsSerializer(label=_('Protocols'), many=True, required=False)
    type_constraints = serializers.ReadOnlyField(required=False, read_only=True)

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'meta', 'comment', 'charset',
            'category', 'category_display',
            'type', 'type_display',
            'su_enabled', 'su_method',
            'ping_enabled', 'ping_method',
            'verify_account_enabled', 'verify_account_method',
            'create_account_enabled', 'create_account_method',
            'change_password_enabled', 'change_password_method',
            'type_constraints',
        ]
        fields_fk = [
            'domain_enabled', 'domain_default',
            'protocols_enabled', 'protocols_default',
        ]
        fields = fields_small + fields_fk
        read_only_fields = [
            'category_display', 'type_display',
        ]


