from copy import deepcopy
from typing import Dict

from rest_framework import serializers

__all__ = [
    'DynamicSerializer'
]


class DynamicSerializer:
    serializer_field_dict = {
        "str": serializers.CharField,
        "dict": serializers.DictField,
        "int": serializers.IntegerField,
        "float": serializers.FloatField,
        "bool": serializers.BooleanField,
        "list": serializers.ListSerializer,
        "datetime": serializers.DateTimeField,
    }

    def __init__(self, name, fields):
        self.name = name
        self.fields = deepcopy(fields)

    @staticmethod
    def generate_field_kwargs(field: dict) -> dict:
        return {k: v for k, v in field.items()}

    def generate_field(self, data_type: str, field_data=None):
        if field_data is None:
            field_data = {}

        serializer_field_dict = self.serializer_field_dict
        field_kwargs = self.generate_field_kwargs(field_data)
        if "[" in data_type:
            type_name, arg_str = data_type[:-1].split("[")
            arg_type = self.generate_field(arg_str)
            serializer_class = self.serializer_field_dict.get(type_name)
            return serializer_class(child=arg_type, **field_kwargs)
        else:
            return serializer_field_dict.get(data_type)(**field_kwargs)

    def yaml_to_serializer(self):
        fields: Dict[str, serializers.Field] = {}
        for field_data in self.fields:
            field_name = field_data.pop('name')
            data_type = field_data.pop('type', 'str')
            fields[field_name] = self.generate_field(data_type, field_data)
        return type(self.name, (serializers.Serializer,), fields)
