from dataclasses import asdict, dataclass, field

from chat_ai.executor.sanitizer import is_sensitive_key


def compact_schema(schema, depth=0):
    if not isinstance(schema, dict) or depth > 5:
        return {}
    keys = (
        'type', 'format', 'enum', 'nullable', 'default', 'minimum', 'maximum',
        'minLength', 'maxLength', 'pattern', 'minItems', 'maxItems',
    )
    compact = {key: schema[key] for key in keys if key in schema}
    if schema.get('description'):
        compact['description'] = str(schema['description'])[:240]
    properties = schema.get('properties') or {}
    if properties:
        compact['properties'] = {
            name: compact_schema(value, depth + 1)
            for name, value in properties.items()
            if not is_sensitive_key(name)
        }
        required = [name for name in (schema.get('required') or []) if name in compact['properties']]
        if required:
            compact['required'] = required
    if schema.get('items'):
        compact['items'] = compact_schema(schema['items'], depth + 1)
    additional = schema.get('additionalProperties')
    if isinstance(additional, dict):
        compact['additionalProperties'] = compact_schema(additional, depth + 1)
    elif isinstance(additional, bool):
        compact['additionalProperties'] = additional
    for key in ('oneOf', 'anyOf', 'allOf'):
        if schema.get(key):
            compact[key] = [compact_schema(item, depth + 1) for item in schema[key][:8]]
    if schema.get('x-request-body-required'):
        compact['x-request-body-required'] = True
    return compact


@dataclass(frozen=True)
class Operation:
    operation_id: str
    method: str
    path: str
    summary: str = ''
    description: str = ''
    tags: tuple[str, ...] = field(default_factory=tuple)
    path_parameters: tuple[dict, ...] = field(default_factory=tuple)
    query_parameters: tuple[dict, ...] = field(default_factory=tuple)
    request_body_schema: dict = field(default_factory=dict)
    response_schema: dict = field(default_factory=dict)
    enabled: bool = True
    risk_level: str = 'read'
    requires_approval: bool = False

    def as_candidate(self, include_schema=False):
        result = {
            'operation_id': self.operation_id,
            'method': self.method,
            'path': self.path,
            'summary': self.summary,
            'description': self.description[:500],
            'tags': list(self.tags),
            'risk_level': self.risk_level,
            'requires_approval': self.requires_approval,
        }
        if include_schema:
            result.update({
                'path_parameters': [
                    {
                        'name': item.get('name'),
                        'required': bool(item.get('required')),
                        'schema': compact_schema(item.get('schema') or {}),
                    }
                    for item in self.path_parameters
                    if not is_sensitive_key(item.get('name'))
                ],
                'query_parameters': [
                    {
                        'name': item.get('name'),
                        'required': bool(item.get('required')),
                        'style': item.get('style') or 'form',
                        'explode': item.get('explode', (item.get('style') or 'form') == 'form'),
                        'schema': compact_schema(item.get('schema') or {}),
                    }
                    for item in self.query_parameters
                    if not is_sensitive_key(item.get('name'))
                ],
                'request_body_schema': compact_schema(self.request_body_schema),
            })
        return result

    def as_dict(self):
        return asdict(self)
