import re

from .operation import Operation
from .resolver import SchemaResolver


HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete'}


class OpenAPIRegistry:
    def __init__(self, schema):
        self.schema = schema
        self.resolver = SchemaResolver(schema)
        self.operations = self._build_operations()

    @staticmethod
    def _fallback_operation_id(method, path):
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', path).strip('_')
        return f'{method.lower()}_{slug}'

    @staticmethod
    def _risk(method):
        if method == 'GET':
            return 'read', False
        if method == 'DELETE':
            return 'dangerous', True
        return 'write', True

    def _parameters(self, path_item, operation):
        parameters = list(path_item.get('parameters') or []) + list(operation.get('parameters') or [])
        parameters = [self.resolver.resolve(item) for item in parameters]
        return (
            tuple(item for item in parameters if item.get('in') == 'path'),
            tuple(item for item in parameters if item.get('in') == 'query'),
        )

    def _request_schema(self, operation):
        body = self.resolver.resolve(operation.get('requestBody') or {})
        content = body.get('content') or {}
        media = content.get('application/json') or content.get('application/*+json') or {}
        schema = media.get('schema') or {}
        schema = self._clean_request_schema(schema)
        if body.get('required') and schema:
            schema = dict(schema)
            schema['x-request-body-required'] = True
        return schema

    @classmethod
    def _clean_request_schema(cls, schema):
        if not isinstance(schema, dict):
            return schema
        cleaned = dict(schema)
        properties = cleaned.get('properties')
        if isinstance(properties, dict):
            writable = {
                name: cls._clean_request_schema(value)
                for name, value in properties.items()
                if not value.get('readOnly')
            }
            removed = set(properties) - set(writable)
            cleaned['properties'] = writable
            if cleaned.get('required'):
                cleaned['required'] = [name for name in cleaned['required'] if name not in removed]
        if isinstance(cleaned.get('items'), dict):
            cleaned['items'] = cls._clean_request_schema(cleaned['items'])
        if isinstance(cleaned.get('additionalProperties'), dict):
            cleaned['additionalProperties'] = cls._clean_request_schema(
                cleaned['additionalProperties']
            )
        for key in ('oneOf', 'anyOf', 'allOf'):
            if isinstance(cleaned.get(key), list):
                cleaned[key] = [cls._clean_request_schema(item) for item in cleaned[key]]
        return cleaned

    def _response_schema(self, operation):
        responses = self.resolver.resolve(operation.get('responses') or {})
        response = responses.get('200') or responses.get('201') or responses.get('202') or responses.get('default') or {}
        content = response.get('content') or {}
        media = content.get('application/json') or content.get('application/*+json') or {}
        return media.get('schema') or {}

    def _build_operations(self):
        result = {}
        for path, path_item in (self.schema.get('paths') or {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, raw_operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(raw_operation, dict):
                    continue
                operation = self.resolver.resolve(raw_operation)
                upper_method = method.upper()
                operation_id = operation.get('operationId') or self._fallback_operation_id(method, path)
                path_parameters, query_parameters = self._parameters(path_item, operation)
                risk_level, requires_approval = self._risk(upper_method)
                result[operation_id] = Operation(
                    operation_id=operation_id,
                    method=upper_method,
                    path=path,
                    summary=operation.get('summary') or '',
                    description=operation.get('description') or '',
                    tags=tuple(operation.get('tags') or ()),
                    path_parameters=path_parameters,
                    query_parameters=query_parameters,
                    request_body_schema=self._request_schema(operation),
                    response_schema=self._response_schema(operation),
                    risk_level=risk_level,
                    requires_approval=requires_approval,
                )
        return result

    def get(self, operation_id):
        return self.operations.get(operation_id)

    def __len__(self):
        return len(self.operations)
