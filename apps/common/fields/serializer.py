# -*- coding: utf-8 -*-
#

import copy
from collections import OrderedDict
from rest_framework.serializers import ALL_FIELDS
from rest_framework import serializers
import six


__all__ = [
    'StringIDField', 'StringManyToManyField', 'ChoiceDisplayField',
    'CustomMetaDictField', 'ReadableHiddenField', 'JSONFieldModelSerializer'
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


class ReadableHiddenField(serializers.HiddenField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.write_only = False

    def to_representation(self, value):
        if hasattr(value, 'id'):
            return getattr(value, 'id')
        return value


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


class JSONFieldModelSerializer(serializers.Serializer):
    """ Model JSONField Serializer"""

    def __init__(self, *args, **kwargs):
        mode_field = getattr(self.Meta, 'model_field', None)
        if mode_field:
            kwargs['label'] = mode_field.field.verbose_name
        super().__init__(*args, **kwargs)

    class Meta:
        model = None
        model_field = None
        fields = None
        exclude = None

    def get_fields(self):
        assert hasattr(self, 'Meta'), (
            'Class {serializer_class} missing "Meta" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        assert hasattr(self.Meta, 'model'), (
            'Class {serializer_class} missing "Meta.model" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )
        model_fields_mapping = {field.name: field for field in self.Meta.model._meta.fields}
        assert hasattr(self.Meta, 'model_field'), (
            'Class {serializer_class} missing "Meta.model_field" attribute'.format(
                serializer_class=self.__class__.__name__
            )
        )

        assert self.Meta.model_field.field.name in model_fields_mapping.keys(), (
            'Class {serializer_class} "Meta.model_field" attribute not in  '
            '"Meta.model._meta.fields"'.format(
                serializer_class=self.__class__.__name__,
            )
        )

        declared_fields = copy.deepcopy(self._declared_fields)

        read_only_field_names = self.get_read_only_field_names()

        field_names = self.get_field_names(declared_fields)

        fields = OrderedDict()
        for field_name in field_names:
            if field_name not in declared_fields:
                continue
            field = declared_fields[field_name]
            if field_name in read_only_field_names:
                setattr(field, 'read_only', True)
            fields[field_name] = field
        return fields

    def get_field_names(self, declared_fields):
        """
        Returns the list of all field names that should be created when
        instantiating this serializer class. This is based on the default
        set of fields, but also takes into account the `Meta.fields` or
        `Meta.exclude` options if they have been specified.
        """

        fields = getattr(self.Meta, 'fields', None)
        exclude = getattr(self.Meta, 'exclude', None)

        if fields and fields != ALL_FIELDS and not isinstance(fields, (list, tuple)):
            raise TypeError(
                'The `fields` option must be a list or tuple or "__all__". '
                'Got %s.' % type(fields).__name__
            )

        if exclude and not isinstance(exclude, (list, tuple)):
            raise TypeError(
                'The `exclude` option must be a list or tuple. Got %s.' %
                type(exclude).__name__
            )

        assert not (fields and exclude), (
            "Cannot set both 'fields' and 'exclude' options on "
            "serializer {serializer_class}.".format(
                serializer_class=self.__class__.__name__
            )
        )

        assert not (fields is None and exclude is None), (
            "Creating a ModelSerializer without either the 'fields' attribute "
            "or the 'exclude' attribute has been deprecated since 3.3.0, "
            "and is now disallowed. Add an explicit fields = '__all__' to the "
            "{serializer_class} serializer.".format(
                serializer_class=self.__class__.__name__
            ),
        )

        if fields == ALL_FIELDS:
            fields = None

        if fields is not None:
            # Ensure that all declared fields have also been included in the
            # `Meta.fields` option.

            # Do not require any fields that are declared in a parent class,
            # in order to allow serializer subclasses to only include
            # a subset of fields.
            required_field_names = set(declared_fields)
            for cls in self.__class__.__bases__:
                required_field_names -= set(getattr(cls, '_declared_fields', []))

            for field_name in required_field_names:
                assert field_name in fields, (
                    "The field '{field_name}' was declared on serializer "
                    "{serializer_class}, but has not been included in the "
                    "'fields' option.".format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )
            return fields

        # Use the default set of field names if `Meta.fields` is not specified.
        fields = self.get_default_field_names(declared_fields)

        if exclude is not None:
            # If `Meta.exclude` is included, then remove those fields.
            for field_name in exclude:
                assert field_name not in self._declared_fields, (
                    "Cannot both declare the field '{field_name}' and include "
                    "it in the {serializer_class} 'exclude' option. Remove the "
                    "field or, if inherited from a parent serializer, disable "
                    "with `{field_name} = None`."
                    .format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )

                assert field_name in fields, (
                    "The field '{field_name}' was included on serializer "
                    "{serializer_class} in the 'exclude' option, but does "
                    "not match any model field.".format(
                        field_name=field_name,
                        serializer_class=self.__class__.__name__
                    )
                )
                fields.remove(field_name)
        return fields

    @staticmethod
    def get_default_field_names(declared_fields):
        return declared_fields

    def get_read_only_field_names(self):
        read_only_fields = getattr(self.Meta, 'read_only_fields', None)
        if read_only_fields is not None:
            if not isinstance(read_only_fields, (list, tuple)):
                raise TypeError(
                    'The `read_only_fields` option must be a list or tuple. '
                    'Got %s.' % type(read_only_fields).__name__
                )
        return read_only_fields

    def to_internal_value(self, data):
        return super().to_internal_value(data)

    def to_representation(self, instance):
        if not isinstance(instance, dict):
            return super().to_representation(instance)
        for field_name, field in self.fields.items():
            if field_name in instance:
                continue
            if field.allow_null:
                continue
            setattr(field, 'allow_null', True)
        return super().to_representation(instance)




