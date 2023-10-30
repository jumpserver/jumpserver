from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

__all__ = [
    'TypeSerializer', 'CategorySerializer', 'ProtocolSerializer'
]


class TypeSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Label'))
    value = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Value'))
    category = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Category'))
    constraints = serializers.JSONField(required=False, allow_null=True, label=_('Constraints'))


class CategorySerializer(serializers.Serializer):
    label = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Label'))
    value = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Value'))
    types = TypeSerializer(many=True, required=False, label=_('Types'), read_only=True)


class ProtocolSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Label'))
    value = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Value'))
