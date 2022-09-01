# -*- coding: utf-8 -*-
#
import six

from rest_framework.fields import ChoiceField
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist

from common.utils import decrypt_password

__all__ = [
    'ReadableHiddenField', 'EncryptedField', 'LabeledChoiceField',
    'ObjectedRelatedField',
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


class LabeledChoiceField(ChoiceField):
    def __init__(self, *args, **kwargs):
        super(LabeledChoiceField, self).__init__(*args, **kwargs)
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

    def to_internal_value(self, data):
        if isinstance(data, dict):
            return data.get('value')
        return super(LabeledChoiceField, self).to_internal_value(data)


class ObjectedRelatedField(serializers.RelatedField):
    def __init__(self, **kwargs):
        self.attrs = kwargs.pop('attrs', None) or ('id', 'name')
        super().__init__(**kwargs)

    def to_representation(self, value):
        data = {}
        for attr in self.attrs:
            data[attr] = getattr(value, attr)
        return data

    def to_internal_value(self, data):
        if isinstance(data, dict):
            pk = data.get(self.attrs[0])
        else:
            pk = data
        queryset = self.get_queryset()
        try:
            if isinstance(data, bool):
                raise TypeError
            return queryset.get(pk=pk)
        except ObjectDoesNotExist:
            self.fail('does_not_exist', pk_value=pk)
        except (TypeError, ValueError):
            self.fail('incorrect_type', data_type=type(pk).__name__)
