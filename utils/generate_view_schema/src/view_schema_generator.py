import os
import json
from django.urls.resolvers import URLPattern, URLResolver
from django.urls import get_resolver

from .url_pattern import CustomURLPattern
from .const import log


__all__ = ['ViewSchemaGenerator']


class ViewSchemaGenerator:

    def __init__(self, output_file_dir):
        os.makedirs(output_file_dir, exist_ok=True)
        self.output_file_dir = output_file_dir
        self.resolver = get_resolver()
        self.url_patterns = self.get_url_patterns()
    
    def get_url_patterns(self):
        return self._extract_url_patterns(self.resolver.url_patterns)
    
    def _extract_url_patterns(self, url_patterns, prefix='/'):
        url_pattern_objects = []
        for pattern in url_patterns:
            if isinstance(pattern, URLResolver):
                resolver = pattern
                _prefix = f'{prefix}{resolver.pattern}'
                patterns = self._extract_url_patterns(resolver.url_patterns, prefix=_prefix)
                url_pattern_objects.extend(patterns)
                continue
            elif isinstance(pattern, URLPattern):
                p = CustomURLPattern(raw=pattern, prefix=prefix)
                url_pattern_objects.append(p)
            else:
                log(f'Unknown pattern type: {type(pattern)}')
        return url_pattern_objects

    def generate(self):
        self.write_url_patterns()
        self.write_webui_schema()
    
    def write_webui_schema(self):
        data = {
            'GET': {},
            'POST': {}
        }
        post_schema = {}
        for pattern in self.url_patterns:
            if pattern.view.requires_auth:
                continue
            url = pattern.full_path
            item = {
                'allowIf': 'prelogin',
                'query': {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False

                },
                'body': {
                    'type': 'object',
                    'properties': pattern.view.write_fields_schema,
                    'required': pattern.view.required_fields,
                    'additionalProperties': False
                }
            }
            post_schema[url] = item
        data['POST'] = post_schema
        self.write_to_file(data, 'webui_schema.json')

    def write_url_patterns(self):
        data = []
        for pattern in self.url_patterns:
            if pattern.view.requires_auth:
                continue
            if pattern.view.view_type == 'function':
                continue
            item = {
                'url': pattern.full_path,
                'view_path': pattern.view.view_path,
                'view_requires_auth': pattern.view.requires_auth,
                'view_type': pattern.view.view_type,
            }
            view_write_fields_schema = pattern.view.write_fields_schema
            if view_write_fields_schema:
                item['view_write_fields_schema'] = view_write_fields_schema
            data.append(item)
        self.write_to_file(data, 'all_url_patterns.json')

    def write_to_file(self, data, filename):
        file_path = os.path.join(self.output_file_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
