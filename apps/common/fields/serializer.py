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
    type_map_fields = {}
    default_type = None
    need_convert_key = False

    def filter_attribute(self, attribute, instance):
        fields = self.type_map_fields.get(instance.type, [])
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

    def convert_value_key(self, dictionary, value):
        if not self.need_convert_key:
            # remote app
            return value
        tp = dictionary.get('type')
        _value = {}
        for k, v in value.items():
            prefix = '{}_'.format(tp)
            _k = k
            if k.lower().startswith(prefix):
                _k = k.lower().split(prefix, 1)[1]
            _k = _k.upper()
            _value[_k] = value[k]
        return _value

    def filter_value_key(self, dictionary, value):
        tp = dictionary.get('type', self.default_type)
        fields = self.type_map_fields.get(tp, [])
        fields_names = [field['name'] for field in fields]
        no_need_keys = [k for k in value.keys() if k not in fields_names]
        for k in no_need_keys:
            value.pop(k)
        return value

    def get_value(self, dictionary):
        """
        反序列化时调用
        """
        value = super().get_value(dictionary)
        value = self.convert_value_key(dictionary, value)
        value = self.filter_value_key(dictionary, value)
        return value
