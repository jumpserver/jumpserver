from rest_framework import serializers

example_info = [
    {"name": "name", "label": "姓名", "required": False, "default": "广州老广", "type": "str"},
    {"name": "age", "label": "年龄", "required": False, "default": 18, "type": "int"},
]

type_field_map = {
    "str": serializers.CharField,
    "password": serializers.CharField,
    "int": serializers.IntegerField,
    "bool": serializers.BooleanField,
    "text": serializers.CharField,
    "choice": serializers.ChoiceField,
    "list": serializers.ListField,
}


def set_default_if_need(data, i):
    field_name = data.pop('name', 'Attr{}'.format(i + 1))
    data['name'] = field_name

    if not data.get('label'):
        data['label'] = field_name
    return data


def set_default_by_type(tp, data, field_info):
    if tp == 'str':
        data['max_length'] = 4096
    elif tp == 'password':
        data['write_only'] = True
    elif tp == 'choice':
        choices = field_info.pop('choices', [])
        if isinstance(choices, str):
            choices = choices.split(',')
        choices = [
            (c, c.title()) if not isinstance(c, (tuple, list)) else c
            for c in choices
        ]
        data['choices'] = choices
    return data


def create_serializer_class(serializer_name, fields_info):
    serializer_fields = {}
    fields_name = ['name', 'label', 'default', 'required', 'type', 'help_text']

    for i, field_info in enumerate(fields_info):
        data = {k: field_info.get(k) for k in fields_name}
        field_type = data.pop('type', 'str')

        # 用户定义 default 和 required 可能会冲突, 所以要处理一下
        default = data.get('default', None)
        if default is None:
            data.pop('default', None)
            data['required'] = True
        elif default == '':
            data['required'] = False
            data['allow_blank'] = True
        else:
            data['required'] = False
        data = set_default_by_type(field_type, data, field_info)
        data = set_default_if_need(data, i)
        if field_type in ['int', 'bool', 'list'] and "allow_blank" in data.keys():
            data.pop('allow_blank')
        field_name = data.pop('name')
        field_class = type_field_map.get(field_type, serializers.CharField)
        serializer_fields[field_name] = field_class(**data)
    return type(serializer_name, (serializers.Serializer,), serializer_fields)
