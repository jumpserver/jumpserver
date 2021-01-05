# -*- coding: utf-8 -*-
#

import copy
from rest_framework import serializers


__all__ = [
    'ReadableHiddenField', 'CustomMetaDictField',
]


# ReadableHiddenField
# -------------------


class ReadableHiddenField(serializers.HiddenField):
    """ 可读的 HiddenField """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.write_only = False

    def to_representation(self, value):
        if hasattr(value, 'id'):
            return getattr(value, 'id')
        return value

#
# OtherField
# ----------


# TODO: DELETE 替换完成后删除
class CustomMetaDictField(serializers.DictField):
    """
    In use:
    RemoteApp params field
    CommandStorage meta field
    ReplayStorage meta field
    """
    type_fields_map = {}
    default_type = None
    convert_key_remove_type_prefix = False
    convert_key_to_upper = False

    def filter_attribute(self, attribute, instance):
        fields = self.type_fields_map.get(instance.type, [])
        for field in fields:
            if field.get('write_only', False):
                attribute.pop(field['name'], None)
        return attribute

    def get_attribute(self, instance):
        """
        序列化时调用
        """
        attribute = super().get_attribute(instance)
        attribute = self.filter_attribute(attribute, instance)
        return attribute

    def convert_value_key_remove_type_prefix(self, dictionary, value):
        if not self.convert_key_remove_type_prefix:
            return value
        tp = dictionary.get('type')
        prefix = '{}_'.format(tp)
        convert_value = {}
        for k, v in value.items():
            if k.lower().startswith(prefix):
                k = k.lower().split(prefix, 1)[1]
            convert_value[k] = v
        return convert_value

    def convert_value_key_to_upper(self, value):
        if not self.convert_key_to_upper:
            return value
        convert_value = {k.upper(): v for k, v in value.items()}
        return convert_value

    def convert_value_key(self, dictionary, value):
        value = self.convert_value_key_remove_type_prefix(dictionary, value)
        value = self.convert_value_key_to_upper(value)
        return value

    def filter_value_key(self, dictionary, value):
        tp = dictionary.get('type')
        fields = self.type_fields_map.get(tp, [])
        fields_names = [field['name'] for field in fields]
        filter_value = {k: v for k, v in value.items() if k in fields_names}
        return filter_value

    @staticmethod
    def strip_value(value):
        new_value = {}
        for k, v in value.items():
            if isinstance(v, str):
                v = v.strip()
            new_value[k] = v
        return new_value

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.convert_value_key(dictionary, value)
        value = self.filter_value_key(dictionary, value)
        value = self.strip_value(value)
        return value


