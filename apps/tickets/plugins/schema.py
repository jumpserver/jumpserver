"""Small form description derived from typed request serializers, not a designer."""
from rest_framework import serializers


def request_fields(serializer):
    result = []
    for name, field in serializer.fields.items():
        item = {'name': name, 'label': str(field.label or name), 'required': field.required,
                'help_text': str(field.help_text or ''), 'type': 'string'}
        if isinstance(field, serializers.ChoiceField):
            item.update(type='choice', choices=[{'value': key, 'label': str(label)} for key, label in field.choices.items()])
        elif isinstance(field, serializers.ListField):
            item['type'] = 'list'
        elif isinstance(field, serializers.IntegerField):
            item.update(type='integer', min=field.min_value, max=field.max_value)
        elif isinstance(field, serializers.DateTimeField):
            item['type'] = 'datetime'
        if field.style.get('resource'):
            item['resource'] = field.style['resource']
        if field.default is not serializers.empty and not callable(field.default):
            item['default'] = field.default
        result.append(item)
    return result
