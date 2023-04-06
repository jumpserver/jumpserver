from rest_framework import serializers

example_info = [
    {"name": "test", "label": "测试", "required": False, "default": "Yes", "type": "str"},
    {"name": "age", "label": "年龄", "required": False, "default": 18, "type": "int"},
]

type_field_map = {
    "str": serializers.CharField,
    "int": serializers.IntegerField,
    "bool": serializers.BooleanField,
    "text": serializers.CharField,
}


def set_default_if_need(data, i):
    field_name = data.pop('name', 'Attr{}'.format(i + 1))
    data['name'] = field_name

    if not data.get('label'):
        data['label'] = field_name


def set_default_by_type(tp, field_info):
    if tp == 'str':
        field_info['max_length'] = 4096


def create_serializer_class(serializer_name, fields_info):
    serializer_fields = {}
    fields_name = ['name', 'label', 'required', 'default', 'type', 'help_text']

    for i, field_info in enumerate(fields_info):
        data = {k: field_info.get(k) for k in fields_name}
        field_type = data.pop('type', 'str')
        set_default_by_type(field_type, data)
        set_default_if_need(data, i)
        field_name = data.pop('name')
        field_class = type_field_map.get(field_type, serializers.CharField)
        serializer_fields[field_name] = field_class(**data)

    return type(serializer_name, (serializers.Serializer,), serializer_fields)
