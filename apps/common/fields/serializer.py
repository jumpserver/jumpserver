# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils import six


__all__ = [
    'StringIDField', 'StringManyToManyField', 'ChoiceDisplayField',
    'CustomMetaDictField'
]


class StringIDField(serializers.Field):
    def to_representation(self, value):
        return {"pk": value.pk, "name": value.__str__()}


class StringManyToManyField(serializers.RelatedField):
    def to_representation(self, value):
        return value.__str__()


class ChoiceDisplayField(serializers.ChoiceField):
    def __init__(self, *args, **kwargs):
        super(ChoiceDisplayField, self).__init__(*args, **kwargs)
        self.choice_strings_to_display = {
            six.text_type(key): value for key, value in self.choices.items()
        }

    def to_representation(self, value):
        if value is None:
            return value
        return {
            'value': self.choice_strings_to_values.get(six.text_type(value), value),
            'display': self.choice_strings_to_display.get(six.text_type(value), value),
        }


class DictField(serializers.DictField):
    def to_representation(self, value):
        if not value or not isinstance(value, dict):
            value = {}
        return super().to_representation(value)


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

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.convert_value_key(dictionary, value)
        value = self.filter_value_key(dictionary, value)
        return value
