# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import DynamicMappingSerializer
from .attrs import attrs_field_dynamic_mapping_serializers

from .. import models

__all__ = [
    'ApplicationSerializer',
    'IncludeDynamicMappingSerializerFieldApplicationSerializerMixin',
]


class IncludeDynamicMappingSerializerFieldApplicationSerializerMixin(serializers.Serializer):
    attrs = DynamicMappingSerializer(mapping_serializers=attrs_field_dynamic_mapping_serializers)

    def get_attrs_mapping_rule(self):
        request = self.context['request']
        query_type = request.query_params.get('type')
        query_category = request.query_params.get('category')
        if query_type:
            mapping_rule = ['type', query_type]
        elif query_category:
            mapping_rule = ['category', query_category]
        else:
            mapping_rule = ['default']
        return mapping_rule


class ApplicationSerializer(IncludeDynamicMappingSerializerFieldApplicationSerializerMixin,
                            BulkOrgResourceModelSerializer):
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

    def validate_attrs(self, attrs):
        _attrs = self.instance.attrs if self.instance else {}
        _attrs.update(attrs)
        return _attrs

