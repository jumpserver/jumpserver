# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

from .. import models

__all__ = [
    'ApplicationSerializer',
]


class ApplicationSerializer(BulkOrgResourceModelSerializer):
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))

    class Meta:
        model = models.Application
        fields = [
            'id', 'name', 'category', 'category_display', 'type', 'type_display', 'attrs',
            'domain', 'created_by', 'date_created', 'date_updated', 'comment'
        ]
        read_only_fields = [
            'created_by', 'date_created', 'date_updated', 'get_type_display',
        ]

    def create(self, validated_data):
        validated_data['attrs'] = validated_data.pop('attrs', {})
        instance = super().create(validated_data)
        return instance

    def update(self, instance, validated_data):
        new_attrs = validated_data.pop('attrs', {})
        instance = super().update(instance, validated_data)
        attrs = instance.attrs
        attrs.update(new_attrs)
        instance.attrs = attrs
        instance.save()
        return instance

