"""Small form description derived from typed request serializers, not a designer."""
from rest_framework import serializers
from django.core.exceptions import ImproperlyConfigured
from common.serializers.fields import TreeChoicesField


def request_fields(serializer):
    result = []
    for name, field in serializer.fields.items():
        if field.read_only:
            continue
        item = {'name': name, 'label': str(field.label or name), 'required': field.required,
                'help_text': str(field.help_text or ''), 'type': 'string'}
        if field.allow_null:
            item['allow_null'] = True
        if isinstance(field, serializers.ChoiceField):
            item.update(type='choice', choices=[{'value': key, 'label': str(label)} for key, label in field.choices.items()])
            if isinstance(field, serializers.MultipleChoiceField):
                item['type'] = 'multiple_choice'
            if isinstance(field, TreeChoicesField):
                item['tree'] = field.tree
        elif isinstance(field, serializers.BooleanField):
            item['type'] = 'boolean'
        elif isinstance(field, serializers.ListField) and isinstance(field.child, (serializers.CharField, serializers.UUIDField)):
            item.update(type='list', max_length=field.max_length)
        elif isinstance(field, serializers.IntegerField):
            item.update(type='integer', min=field.min_value, max=field.max_value)
        elif isinstance(field, serializers.DateTimeField):
            item['type'] = 'datetime'
        elif not isinstance(field, (serializers.CharField, serializers.UUIDField)):
            raise ImproperlyConfigured(
                f'Unsupported ticket field {name}: {type(field).__name__}. Use a custom form or a supported field.'
            )
        if field.style.get('resource'):
            item['resource'] = field.style['resource']
            if item['resource'] not in ('asset', 'account', 'session', 'node', 'account_selector'):
                raise ImproperlyConfigured(f'Unsupported ticket resource field: {name}. Use a custom form.')
            if item['resource'] == 'account':
                dependency = field.style.get('depends_on')
                if dependency not in serializer.fields or serializer.fields[dependency].style.get('resource') != 'asset':
                    raise ImproperlyConfigured(f'Account field {name} must declare an asset depends_on field.')
                item['depends_on'] = dependency
        if field.default is not serializers.empty and not callable(field.default):
            item['default'] = field.default
        result.append(item)
    return result
