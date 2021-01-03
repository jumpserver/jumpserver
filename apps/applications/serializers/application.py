# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.fields import DynamicMappingField
from .attrs import get_attrs_field_dynamic_mapping_rules

from .. import models

__all__ = [
    'ApplicationSerializer',
]


class ApplicationSerializer(BulkOrgResourceModelSerializer):
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))
    attrs = DynamicMappingField(mapping_rules=get_attrs_field_dynamic_mapping_rules())

    class Meta:
        model = models.Application
        fields = [
            'id', 'name', 'category', 'category_display', 'type', 'type_display', 'attrs',
            'domain', 'created_by', 'date_created', 'date_updated', 'comment'
        ]
        read_only_fields = [
            'created_by', 'date_created', 'date_updated', 'get_type_display',
        ]

    def validate_attrs(self, attrs):
        _attrs = self.instance.attrs if self.instance else {}
        _attrs.update(attrs)
        return _attrs
