import os
import json
from .endpoint import Endpoint, MethodSchema, QueryField, BodyField

dirname = os.path.dirname
BASE_DIR = dirname(dirname(dirname(os.path.abspath(__file__))))
OUTPUT_FILE_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)


def write_to_file(data, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def write_webui_schema(endpoints):
    filename = 'webui_schema.json'
    file_path = os.path.join(OUTPUT_FILE_DIR, filename)
    data = {
        'GET': {},
        'POST': {}
    }
    for e in endpoints:
        e: Endpoint
        if e.requires_auth:
            continue
        url = e.path
        if url.startswith('/api/v1/users/^users'):
            pass
        for method, method_schema in e.methods.items():
            item = {
                'allowIf': 'prelogin',
            }
            method_schema: MethodSchema
            query_properties = {}
            for field in method_schema.query_fields:
                field: QueryField
                query_properties[field.name] = {
                    'type': field.field_type,
                    'description': field.description
                }
            query = {
                "type": "object",
                "properties":  query_properties,
                "required": [],
                "additionalProperties": False
            }
            item['query'] = query
            if method in ['POST']:
                body_properties = {}
                for field in method_schema.body_fields:
                    field: BodyField
                    body_properties[field.name] = {
                        'type': field.field_type,
                        'description': field.description
                    }
                body = {
                    'type': 'object',
                    'properties': body_properties,
                    'required': [],
                    "additionalProperties": False
                }
                item['body'] = body

            data[method][url] = item

    write_to_file(data, file_path)


def render_schema(endpoints):
    write_webui_schema(endpoints)
