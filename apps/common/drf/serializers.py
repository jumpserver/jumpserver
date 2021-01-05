import copy
from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework.serializers import ModelSerializer
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkListSerializerMixin
from django.utils.functional import cached_property
from rest_framework.utils.serializer_helpers import BindingDict
from common.mixins.serializers import BulkSerializerMixin
from common.utils import QuickLookupDict

__all__ = [
    'DynamicMappingSerializer',
    'EmptySerializer', 'BulkModelSerializer', 'AdaptedBulkListSerializer', 'CeleryTaskSerializer'
]


# DynamicMappingSerializer
# ------------------------


class DynamicMappingSerializer(serializers.Serializer):
    data_type_error_messages = 'Expect get instance of type `{}`, but got instance type of  `{}`'

    def __init__(self, mapping_serializers=None, get_mapping_serializers_method_name=None,
                 get_mapping_path_method_name=None, default_serializer=None, **kwargs):
        self.mapping_serializers = mapping_serializers
        self.get_mapping_serializers_method_name = get_mapping_serializers_method_name
        self.get_mapping_path_method_name = get_mapping_path_method_name
        self.default_serializer = default_serializer or serializers.Serializer
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        # The get mapping serializers method name defaults to `get_{field_name}_mapping_serializers`
        if self.get_mapping_serializers_method_name is None:
            method_name = 'get_{field_name}_mapping_serializers'.format(field_name=field_name)
            self.get_mapping_serializers_method_name = method_name

        # The get mapping rule method name defaults to `get_{field_name}_mapping_path`.
        if self.get_mapping_path_method_name is None:
            method_name = 'get_{field_name}_mapping_path'.format(field_name=field_name)
            self.get_mapping_path_method_name = method_name

        super().bind(field_name, parent)

    def get_mapping_serializers(self):
        if self.mapping_serializers is not None:
            return self.mapping_serializers
        method = getattr(self.parent, self.get_mapping_serializers_method_name)
        return method()

    def get_mapping_path(self, mapping_serializers):
        method = getattr(self.parent, self.get_mapping_path_method_name)
        return method(mapping_serializers)

    @staticmethod
    def mapping(mapping_serializers, mapping_path):
        quick_lookup_dict = QuickLookupDict(data=mapping_serializers)
        serializer = quick_lookup_dict.get(key_path=mapping_path)
        return serializer

    def get_mapped_serializer(self):
        mapping_serializers = self.get_mapping_serializers()
        assert isinstance(mapping_serializers, dict), (
            self.data_type_error_messages.format('dict', type(mapping_serializers))
        )
        mapping_path = self.get_mapping_path(mapping_serializers)
        assert isinstance(mapping_path, list), (
            self.data_type_error_messages.format('list', type(mapping_path))
        )
        serializer = self.mapping(mapping_serializers, mapping_path)
        return serializer

    @cached_property
    def mapped_serializer(self):
        serializer = self.get_mapped_serializer()
        if serializer is None:
            serializer = self.default_serializer
        if isinstance(serializer, type):
            serializer = serializer()
        return serializer

    def get_fields(self):
        fields = self.mapped_serializer.get_fields()
        return fields

    @cached_property
    def fields(self):
        """
        重写此方法因为在 BindingDict 中要设置每一个 field 的 parent 为 `mapped_serializer`,
        这样在调用 field.parent 时, 才会达到预期的结果，
        比如: serializers.SerializerMethodField
        """
        fields = BindingDict(self.mapped_serializer)
        for key, value in self.get_fields().items():
            fields[key] = value
        return fields


#
# Other Serializer
# ----------------


class EmptySerializer(Serializer):
    pass


class BulkModelSerializer(BulkSerializerMixin, ModelSerializer):
    pass


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass


class CeleryTaskSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)


