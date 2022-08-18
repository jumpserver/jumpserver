# -*- coding: utf-8 -*-
#
import six

from rest_framework.fields import ChoiceField
from rest_framework import serializers

from common.utils import decrypt_password

__all__ = [
    'ReadableHiddenField', 'EncryptedField', 'ChoiceDisplayField'
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


class EncryptedField(serializers.CharField):
    def __init__(self, write_only=None, **kwargs):
        if write_only is None:
            write_only = True
        kwargs['write_only'] = write_only
        super().__init__(**kwargs)

    def to_internal_value(self, value):
        value = super().to_internal_value(value)
        return decrypt_password(value)


class ChoiceDisplayField(ChoiceField):
    def __init__(self, *args, **kwargs):
        super(ChoiceDisplayField, self).__init__(*args, **kwargs)
        self.choice_mapper = {
            six.text_type(key): value for key, value in self.choices.items()
        }

    def to_representation(self, value):
        if value in ('', None):
            return value
        return {
            'value': value,
            'label': self.choice_mapper.get(six.text_type(value), value),
        }
