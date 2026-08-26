import re
from urllib.parse import quote

from rest_framework.exceptions import ValidationError


def _validate_scalar(value, schema, location):
    expected = schema.get('type')
    nullable = schema.get('nullable') or 'null' in (schema.get('type') if isinstance(schema.get('type'), list) else [])
    if value is None:
        if nullable or not expected:
            return
        raise ValidationError({location: 'This value may not be null.'})
    expected_types = expected if isinstance(expected, list) else [expected]

    def matches(item):
        if item == 'integer':
            return isinstance(value, int) and not isinstance(value, bool)
        if item == 'number':
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        type_map = {'string': str, 'boolean': bool, 'array': list, 'object': dict}
        return item in type_map and isinstance(value, type_map[item])

    if expected and not any(matches(item) for item in expected_types):
        raise ValidationError({location: f'Expected {expected}.'})
    if schema.get('enum') and value not in schema['enum']:
        raise ValidationError({location: f'Value must be one of {schema["enum"]}.'})
    if isinstance(value, str):
        if schema.get('minLength') is not None and len(value) < schema['minLength']:
            raise ValidationError({location: f'Minimum length is {schema["minLength"]}.'})
        if schema.get('maxLength') is not None and len(value) > schema['maxLength']:
            raise ValidationError({location: f'Maximum length is {schema["maxLength"]}.'})
        if schema.get('pattern') and not re.search(schema['pattern'], value):
            raise ValidationError({location: 'Value does not match the required pattern.'})
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if schema.get('minimum') is not None and value < schema['minimum']:
            raise ValidationError({location: f'Minimum value is {schema["minimum"]}.'})
        if schema.get('maximum') is not None and value > schema['maximum']:
            raise ValidationError({location: f'Maximum value is {schema["maximum"]}.'})


def validate_json(value, schema, location='body'):
    if not schema:
        return
    for variant_name, variants in (
        ('oneOf', schema.get('oneOf') or []),
        ('anyOf', schema.get('anyOf') or []),
    ):
        if not variants:
            continue
        errors = []
        matches = 0
        for variant in variants:
            try:
                validate_json(value, variant, location)
                matches += 1
            except ValidationError as exc:
                errors.append(exc.detail)
        if matches == 0:
            raise ValidationError({
                location: f'Value does not match any {variant_name} schema.',
                'variants': errors[:3],
            })
        if variant_name == 'oneOf' and matches != 1:
            raise ValidationError({location: 'Value matches more than one oneOf schema.'})
    for variant in schema.get('allOf') or []:
        validate_json(value, variant, location)
    _validate_scalar(value, schema, location)
    if isinstance(value, dict):
        properties = schema.get('properties') or {}
        required = set(schema.get('required') or [])
        missing = sorted(required - set(value))
        if missing:
            raise ValidationError({location: f'Missing required fields: {", ".join(missing)}.'})
        if properties:
            unknown = sorted(set(value) - set(properties))
        else:
            unknown = sorted(value)
        additional = schema.get('additionalProperties', None)
        if unknown and (additional is False or (properties and additional is None)):
            raise ValidationError({location: f'Unknown fields: {", ".join(unknown)}.'})
        for key, item in value.items():
            child_schema = properties.get(key)
            if child_schema:
                validate_json(item, child_schema, f'{location}.{key}')
            elif isinstance(additional, dict):
                validate_json(item, additional, f'{location}.{key}')
    elif isinstance(value, list):
        if schema.get('minItems') is not None and len(value) < schema['minItems']:
            raise ValidationError({location: f'Minimum item count is {schema["minItems"]}.'})
        if schema.get('maxItems') is not None and len(value) > schema['maxItems']:
            raise ValidationError({location: f'Maximum item count is {schema["maxItems"]}.'})
        if schema.get('items'):
            for index, item in enumerate(value):
                validate_json(item, schema['items'], f'{location}[{index}]')


class RequestBuilder:
    @staticmethod
    def _query_scalar(value):
        if value is None:
            return ''
        if isinstance(value, bool):
            return 'true' if value else 'false'
        return str(value)

    def serialize_query(self, operation, query_params):
        parameters = {item.get('name'): item for item in operation.query_parameters}
        serialized = []
        for name, value in query_params.items():
            parameter = parameters[name]
            style = parameter.get('style') or 'form'
            explode = parameter.get('explode')
            if explode is None:
                explode = style == 'form'

            if isinstance(value, list):
                items = [self._query_scalar(item) for item in value]
                if style == 'form' and explode:
                    serialized.extend((name, item) for item in items)
                elif style == 'form':
                    serialized.append((name, ','.join(items)))
                elif style == 'spaceDelimited':
                    serialized.append((name, ' '.join(items)))
                elif style == 'pipeDelimited':
                    serialized.append((name, '|'.join(items)))
                else:
                    raise ValidationError({f'query_params.{name}': f'Unsupported query style: {style}.'})
                continue

            if isinstance(value, dict):
                if style == 'deepObject':
                    serialized.extend(
                        (f'{name}[{key}]', self._query_scalar(item))
                        for key, item in value.items()
                    )
                elif style == 'form' and explode:
                    serialized.extend(
                        (str(key), self._query_scalar(item))
                        for key, item in value.items()
                    )
                elif style == 'form':
                    flattened = []
                    for key, item in value.items():
                        flattened.extend((str(key), self._query_scalar(item)))
                    serialized.append((name, ','.join(flattened)))
                else:
                    raise ValidationError({f'query_params.{name}': f'Unsupported query style: {style}.'})
                continue

            serialized.append((name, self._query_scalar(value)))
        return serialized

    def build(self, operation, arguments):
        if not isinstance(arguments, dict):
            raise ValidationError({'arguments': 'Must be an object.'})
        path_params = arguments.get('path_params') or {}
        query_params = arguments.get('query_params') or {}
        body = arguments.get('body', {})
        if not isinstance(path_params, dict) or not isinstance(query_params, dict):
            raise ValidationError({'arguments': 'path_params and query_params must be objects.'})

        path = operation.path
        allowed_path = {item.get('name'): item for item in operation.path_parameters}
        for name, parameter in allowed_path.items():
            if parameter.get('required') and name not in path_params:
                raise ValidationError({'path_params': f'Missing required path parameter: {name}.'})
            if name in path_params:
                _validate_scalar(path_params[name], parameter.get('schema') or {}, f'path_params.{name}')
                path = path.replace('{' + name + '}', quote(str(path_params[name]), safe=''))
        unknown_path = sorted(set(path_params) - set(allowed_path))
        if unknown_path or '{' in path or '}' in path:
            raise ValidationError({'path_params': f'Invalid path parameters: {unknown_path}.'})

        allowed_query = {item.get('name'): item for item in operation.query_parameters}
        unknown_query = sorted(set(query_params) - set(allowed_query))
        if unknown_query:
            raise ValidationError({'query_params': f'Unknown query parameters: {", ".join(unknown_query)}.'})
        missing_query = sorted(
            name for name, parameter in allowed_query.items()
            if parameter.get('required') and name not in query_params
        )
        if missing_query:
            raise ValidationError({'query_params': f'Missing required query parameters: {", ".join(missing_query)}.'})
        for name, value in query_params.items():
            validate_json(value, (allowed_query[name].get('schema') or {}), f'query_params.{name}')

        if operation.request_body_schema:
            validate_json(body, operation.request_body_schema)
        elif body not in ({}, None):
            raise ValidationError({'body': 'This operation does not accept a JSON body.'})
        if not path.startswith('/api/v1/'):
            raise ValidationError({'path': 'Only Core API v1 operations are allowed.'})
        return path, query_params, body
