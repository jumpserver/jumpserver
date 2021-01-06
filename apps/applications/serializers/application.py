# coding: utf-8
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import MethodSerializer
from .attrs import category_serializer_classes_mapping, type_serializer_classes_mapping

from .. import models

__all__ = [
    'ApplicationSerializer',
    'IncludeMethodSerializerFieldApplicationSerializerMixin',
]


class IncludeMethodSerializerFieldApplicationSerializerMixin(serializers.Serializer):
    attrs = MethodSerializer()

    def get_attrs_serializer(self):
        request = self.context['request']
        query_type = request.query_params.get('type')
        query_category = request.query_params.get('category')
        if query_type:
            serializer_class = type_serializer_classes_mapping.get(query_type)
        elif query_category:
            serializer_class = category_serializer_classes_mapping.get(query_category)
        else:
            serializer_class = None
        if serializer_class is None:
            serializer_class = serializers.Serializer
        serializer = serializer_class()
        return serializer


class ApplicationSerializer(IncludeMethodSerializerFieldApplicationSerializerMixin,
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

