# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils import six


__all__ = ['StringIDField', 'StringManyToManyField', 'ChoiceDisplayField']


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
