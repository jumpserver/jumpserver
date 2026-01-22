import os
import json
import sys
import django

# 获取项目根目录（jumpserver 目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
APP_DIR = os.path.join(BASE_DIR, 'apps')


# 不改变工作目录，直接加入 sys.path
sys.path.insert(0, APP_DIR)
sys.path.insert(0, BASE_DIR)

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from django.core.handlers.asgi import ASGIRequest
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.permissions import OperandHolder, AND, OR, NOT
from rbac.permissions import RBACPermission

dirname = os.path.dirname

BASE_DIR = dirname(dirname(os.path.abspath(__file__)))
OUTPUT_FILE_DIR = os.path.join(BASE_DIR, 'output')
os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)


scope = {
    'type': 'http',
    'method': 'GET',
    'path': '/',
    'query_string': b'',
    'headers': [],
}
async def receive():
    return {'type': 'http.request', 'body': b''}
fake_request = ASGIRequest(scope, receive)
setattr(fake_request, 'query_params', {})


def extract_url_patterns(patterns, path_prefix='/'):
    routes = []
    for p in patterns:
        if isinstance(p, URLResolver):
            _path_prefix = f'{path_prefix}{p.pattern}'
            _routes = extract_url_patterns(p.url_patterns, path_prefix=_path_prefix)
            routes.extend(_routes)
        elif isinstance(p, URLPattern):
            setattr(p, 'path_full', f'{path_prefix}{p.pattern}')
            routes.append(p)
        else:
            print(f'Skip: unknown pattern type: {type(p)}')
    return routes


def discover_routes():
    resolver = get_resolver()
    routes = extract_url_patterns(resolver.url_patterns)
    return routes


def resolve_view_class(view_func):
    view_class = getattr(view_func, 'view_class', None)
    if not view_class:
        view_class = getattr(view_func, 'cls', None)
    return view_class


def check_permission_class_requires_auth(permission_class):
    if isinstance(permission_class, OperandHolder):
        operator  = permission_class.operator_class
        op1_class = permission_class.op1_class
        op2_class = permission_class.op2_class
        permission_classes = [op1_class, op2_class]
        return check_permission_classes_requires_auth(permission_classes, operator)
    else:
        if issubclass(permission_class, (IsAuthenticated, RBACPermission)):
            return True
        if issubclass(permission_class, (AllowAny, )):
            return False

        permission_class_name: str = getattr(permission_class, '__name__', None)
        if not permission_class_name:
            return False
        if 'Authenticated' in permission_class_name:
            return True
        if permission_class_name.startswith('UserConfirmation'):
            return True
        return False


def check_permission_classes_requires_auth(permission_classes, operator):
    if operator == AND:
        for pc in permission_classes:
            if check_permission_class_requires_auth(pc):
                return True
        return False

    if operator == OR:
        for pc in permission_classes:
            if not check_permission_class_requires_auth(pc):
                return False
        return True

    if operator == NOT:
        raise ValueError('NOT operator is not supported in permission_classes')

    return False

def is_required_auth(view_func):
    view_class = resolve_view_class(view_func)
    if view_class:
        if issubclass(view_class, LoginRequiredMixin):
            return True
        permission_classes = getattr(view_class, 'permission_classes', [])
        if not permission_classes:
            return False
        return check_permission_classes_requires_auth(permission_classes, operator=AND)
    # func base view
    return False

def get_view_http_methods(view_func):
    view_class = resolve_view_class(view_func)
    has_get_method = True
    if not view_class:
        # function based view
        http_method_names = ['GET']
        return http_method_names
    view = view_class(request=fake_request)
    http_method_names = getattr(view, '_allowed_methods', lambda: [])()
    if http_method_names:
        return http_method_names
    http_method_names = getattr(view, 'http_method_names', [])
    if http_method_names:
        return http_method_names
    http_method_names = []
    has_get_method = hasattr(view_class, 'get') or hasattr(view_class, 'list') or hasattr(view_class, 'retrieve')
    if has_get_method:
        http_method_names.append('GET')
    has_post_method = hasattr(view_class, 'post') or hasattr(view_class, 'create')
    if has_post_method:
        http_method_names.append('POST')
    return http_method_names

from rest_framework import serializers
from django import forms

field_type_mapper = {
    'object': [serializers.Serializer, serializers.ModelSerializer],
    'string': [serializers.CharField, forms.CharField],
    'integer': [serializers.IntegerField, forms.IntegerField],
    'boolean': [serializers.BooleanField, forms.BooleanField],
}

def get_field_type(field):
    for json_type, class_list in field_type_mapper.items():
        if isinstance(field, tuple(class_list)):
            return json_type
    return 'string'


def get_view_query_properties(view_func):
    view_class = resolve_view_class(view_func)
    if not view_class:
        # function based view
        return {}
    query_serializer_class = getattr(view_class, 'query_serializer_class', None)
    if not query_serializer_class:
        return {}
    serializer = query_serializer_class()
    fields = serializer.get_fields()
    properties = {}
    for name, field in fields.items():
        field_schema = {}
        field_schema['type'] = get_field_type(field)
        help_text = getattr(field, 'help_text', '')
        if help_text:
            field_schema['description'] = str(help_text)
        properties[name] = field_schema
    return properties


def get_view_query_schema(view_func):
    query_properties = get_view_query_properties(view_func)
    query_schema = {
        'type': 'object',
        'properties': query_properties,
        'additionalProperties': False,
    }
    return query_schema


def generate_view_schema(view_func):
    http_method_names = get_view_http_methods(view_func)
    schema = {}
    if 'GET' in http_method_names:
        schema['GET'] = {}
        query_schema = get_view_query_schema(view_func)
        if query_schema:
            schema['GET']['query'] = query_schema
    if 'POST' in http_method_names:
        schema['POST'] = {}
    return schema


def write_schema(schema):
    filename = 'x_webui_schema.json'
    file_path = os.path.join(OUTPUT_FILE_DIR, filename)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, indent=4, ensure_ascii=False)


def generate_schema():
    schema = {
        'GET': {},
        'POST': {}
    }
    routes = discover_routes()
    for route in routes:
        url = route.path_full
        view_func = route.callback
        if is_required_auth(view_func):
            continue
        view_schema = generate_view_schema(view_func)
        if 'GET' in view_schema:
            schema['GET'][url] = {
                **view_schema['GET'],
                'allowIf': 'prelogin'
            }
        if 'POST' in view_schema:
            schema['POST'][url] = {
                **view_schema['POST'],
                'allowIf': 'prelogin'
            }
    write_schema(schema)


if __name__ == '__main__':
    generate_schema()
