from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class TypeSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('id'))
    name = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Name'))
    category = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Category'))
    constraints = serializers.JSONField(required=False, allow_null=True, label=_('Constraints'))


class CategorySerializer(serializers.Serializer):
    id = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('id'))
    name = serializers.CharField(max_length=64, required=False, allow_blank=True, label=_('Name'))
    children = TypeSerializer(many=True, required=False, label=_('Children'), read_only=True)
