import json
import os
import sys
from turtle import up

import django
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver

# 获取项目根目录（jumpserver 目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP_DIR = os.path.join(BASE_DIR, 'apps')

# 不改变工作目录，直接加入 sys.path
sys.path.insert(0, APP_DIR)
sys.path.insert(0, BASE_DIR)

# 设置 Django 环境
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "jumpserver.settings")
django.setup()

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE_DIR = os.path.join(CURRENT_DIR, 'output')
os.makedirs(OUTPUT_FILE_DIR, exist_ok=True)

from rest_framework.views import APIView
from rest_framework.permissions import OperandHolder, AND, OR, NOT
from django.views.generic.base import View
from django.views.generic.edit import FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.handlers.asgi import ASGIRequest

from rest_framework.permissions import AllowAny, IsAuthenticated
from rbac.permissions import RBACPermission
from common.utils import lazyproperty
# 尝试使用模拟请求
scope = {
    'type': 'http',
    'method': 'GET',
    'path': '/',
    'query_string': b'',
    'headers': [],
}

async def receive():
    return {'type': 'http.request', 'body': b''}

request = ASGIRequest(scope, receive)


def log(message):
    print(message)


class FieldsGenerator:

    def write_fields_schema(self):
        return {}

    def required_fields(self):
        return []


class FormFieldsGenerator(FieldsGenerator):
    def __init__(self, raw_class, view):
        self.raw_class = raw_class
        self.view = view

    
    @lazyproperty
    def fields(self):
        return self.raw_class().fields

    def write_fields_schema(self):
        schema = self.get_fields_schema(self.fields)
        return schema

    def required_fields(self):
        fields = [name for name, field in self.fields.items() if field.required]
        return fields
    
    def get_fields_schema(self, fields):
        schemas = {}
        for name, field in fields.items():
            schema = {
                'type': self.get_field_type(field),
            }
            description = getattr(field, 'help_text', '')
            if description:
                schema['description'] = str(description)
            schemas[name] = schema
        return schemas
    
    def get_field_type(self, field):
        """将 Django Form Field 类型映射到 JSON Schema 类型"""
        from django import forms
        
        type_mapping = {
            forms.CharField: 'string',
            forms.EmailField: 'string',
            forms.URLField: 'string',
            forms.SlugField: 'string',
            forms.UUIDField: 'string',
            forms.RegexField: 'string',
            forms.FileField: 'string',
            forms.ImageField: 'string',
            forms.FilePathField: 'string',
            forms.GenericIPAddressField: 'string',
            forms.IntegerField: 'integer',
            forms.FloatField: 'number',
            forms.DecimalField: 'number',
            forms.BooleanField: 'boolean',
            forms.NullBooleanField: 'boolean',
            forms.DateField: 'string',
            forms.TimeField: 'string',
            forms.DateTimeField: 'string',
            forms.DurationField: 'string',
            forms.MultipleChoiceField: 'array',
            forms.TypedMultipleChoiceField: 'array',
            forms.ModelMultipleChoiceField: 'array',
            forms.ChoiceField: 'string',
            forms.TypedChoiceField: 'string',
            forms.ModelChoiceField: 'string',
            forms.JSONField: 'object',
        }
        
        for field_type, json_type in type_mapping.items():
            if isinstance(field, field_type):
                return json_type
        
        return 'string'


class SerializerFieldsGenerator(FieldsGenerator):

    def __init__(self, raw_class, view):
        self.raw_class = raw_class
        self.view = view
    
    @lazyproperty
    def fields(self):
        fields = {}
        try:
            fields = self.raw_class().fields
        except Exception as e:
            if hasattr(self.raw_class, '_declared_fields'):
                fields = self.raw_class._declared_fields
        return fields
    
    @lazyproperty
    def write_fields(self):
        fields = {}
        for name, field in self.fields.items():
            if field.read_only:
                continue
            fields[name] = field
        return fields
    
    def get_fields_schema(self, fields):
        schemas = {}
        if not hasattr(fields, 'items'):
            return {}
        for name, field in fields.items():
            schema = self.get_field_schema(field)
            if hasattr(field, 'child'):
                _fields = field.child
                _fields_schema = self.get_fields_schema(_fields)
                schema['properties'] = _fields_schema
            schemas[name] = schema
        return schemas
    
    def get_field_schema(self, field):
        schema = {
            'type': self.get_field_type(field),
        }
        if description := getattr(field, 'help_text', ''):
            schema['description'] = str(description)
        extra_schema = self.get_field_extra_schema(field)
        schema.update(extra_schema)
        return schema
    
    def field_is_nested(self, field):
        from rest_framework import serializers
        nested_field_types = (
            serializers.Serializer,
            serializers.ModelSerializer,
        )
        return isinstance(field, nested_field_types)
    
    def get_field_extra_schema(self, field):
        """获取字段的正则表达式模式"""
        patterns = {}
        # 检查 validators 中是否有正则验证器
        if hasattr(field, 'validators'):
            for validator in field.validators:
                if hasattr(validator, 'regex'):
                    patterns['pattern'] = str(validator.regex.pattern)
                    break
        # 针对特定字段类型添加模式
        from rest_framework import serializers
        if isinstance(field, serializers.EmailField):
            patterns['format'] = 'email'
        elif isinstance(field, serializers.URLField):
            patterns['format'] = 'uri'
        elif isinstance(field, (serializers.DateTimeField, serializers.DateField, serializers.TimeField)):
            patterns['format'] = 'date-time'

        # 添加长度限制
        if hasattr(field, 'max_length') and field.max_length:
            patterns['maxLength'] = field.max_length
        if hasattr(field, 'min_length') and field.min_length:
            patterns['minLength'] = field.min_length
        
        # 添加数值范围
        if hasattr(field, 'max_value') and field.max_value is not None:
            patterns['maximum'] = field.max_value
        if hasattr(field, 'min_value') and field.min_value is not None:
            patterns['minimum'] = field.min_value
        
        if choices := self.get_field_choices(field):
            patterns['enum'] = choices
        return patterns
    
    def get_field_choices(self, field):
        from rest_framework import serializers
        choices = []
        field_need_query_db = isinstance(field, (
            serializers.PrimaryKeyRelatedField,  # 会查询数据库
            serializers.StringRelatedField,      # 会查询数据库
            serializers.SlugRelatedField,        # 会查询数据库
            serializers.HyperlinkedRelatedField, # 会查询数据库
            serializers.HyperlinkedIdentityField,# 会查询数据库
            serializers.RelatedField,            # 基类，会查询数据库
            serializers.ManyRelatedField,        # 会查询数据库
            serializers.ListSerializer           # 可能会查询数据库
        ))
        if field_need_query_db:
            return choices  # 不返回需要查询数据库的字段选项

        choices = getattr(field, 'choices', [])
        if not choices:
            return choices
        
        if isinstance(choices, dict):
            # choices 可能是字典、列表或元组
            choices = list(choices.keys())
        elif isinstance(choices, (list, tuple)):
            # choices 可能是 [(value, label), ...] 或 [value, ...]
            for choice in choices:
                if isinstance(choice, (list, tuple)) and len(choice) == 2:
                    choices.append(choice[0])
                else:
                    choices.append(choice)
        return choices
    
    def get_field_type(self, field):
        """将 Python 字段类型映射到 JSON Schema 类型"""
        from rest_framework import serializers

        if self.field_is_nested(field):
            return 'object'
        
        type_mapping = {
            serializers.CharField: 'string',
            serializers.EmailField: 'string',
            serializers.URLField: 'string',
            serializers.UUIDField: 'string',
            serializers.SlugField: 'string',
            serializers.ChoiceField: 'string',
            serializers.IntegerField: 'integer',
            serializers.FloatField: 'number',
            serializers.DecimalField: 'number',
            serializers.BooleanField: 'boolean',
            serializers.DateTimeField: 'string',
            serializers.DateField: 'string',
            serializers.TimeField: 'string',
            serializers.ListField: 'array',
            serializers.DictField: 'object',
            serializers.JSONField: 'object',
        }
        
        for field_type, json_type in type_mapping.items():
            if isinstance(field, field_type):
                return json_type
        
        return 'string'  # 默认类型

    def write_fields_schema(self):
        fields = self.write_fields
        if not fields:
            return {}
        schema = self.get_fields_schema(fields)
        return schema
    
    def required_fields(self):
        required = []
        for name, field in self.write_fields.items():
            if field.required:
                required.append(name)
        return required


class CustomView:

    def __init__(self, view_func):
        self.view_func = view_func
    
    @property
    def view_class(self):
        cls = getattr(self.view_func, 'view_class', None)
        if not cls:
            cls = getattr(self.view_func, 'cls', None)
        return cls
    
    @property
    def view_path(self):
        if self.view_class:
            v = self.view_class
        else:
            v = self.view_func
        return f'{v.__module__}.{v.__name__}'
    
    @property
    def view_type(self):
        if self.view_class:
            return 'class'
        else:
            return 'function'
    
    @lazyproperty
    def fields_generator(self):
        generator = None
        if self.view_class:
            if issubclass(self.view_class, FormView):
                generator = self.get_form_fields_generator()
            if issubclass(self.view_class, APIView):
                generator= self.get_serializer_fields_generator()
        if not generator:
            generator = FieldsGenerator()
        return generator
    
    @property
    def write_fields_schema(self):
         return self.fields_generator.write_fields_schema()
    
    @property
    def required_fields(self):
        return self.fields_generator.required_fields()
    
    def get_form_fields_generator(self):
        if hasattr(self.view_class, 'get_comprehensive_form_class'):
            view_instance = self.view_class(request=request)
            form_class = view_instance.get_comprehensive_form_class()
        else:
            form_class = getattr(self.view_class, 'form_class', None)
            if not form_class:
                if hasattr(self.view_class, 'get_form_class'):
                    # TODO: 实例化 view 类需要传入 request 参数
                    view_instance = self.view_class(request=request)
                    form_class = view_instance.get_form_class()
        if form_class:
            return FormFieldsGenerator(raw_class=form_class, view=self)

    def get_serializer_fields_generator(self):
        serializer_class = getattr(self.view_class, 'serializer_class', None)
        if not serializer_class:
            if hasattr(self.view_class, 'get_serializer_class'):
                # TODO: 实例化 view 类需要传入 request 参数
                view_instance = self.view_class(request=request)
                serializer_class = view_instance.get_serializer_class()
        if serializer_class:
            return SerializerFieldsGenerator(raw_class=serializer_class, view=self)

    @property
    def query_fields_schema(self):
        return {}

    @lazyproperty
    def requires_auth(self):
        if self.view_class:
            return self.check_view_class_requires_auth()
        else:
            return self.check_view_func_requires_auth()
    
    def check_view_class_requires_auth(self):
        if issubclass(self.view_class, LoginRequiredMixin):
            return True

        permission_classes = getattr(self.view_class, 'permission_classes', [])
        if not permission_classes:
            return False
        
        return self.check_permission_classes_requires_auth(permission_classes)
    
    def check_permission_classes_requires_auth(self, permission_classes, operator=AND):
        if operator == AND:
            for pc in permission_classes:
                if self.check_permission_class_requires_auth(pc):
                    return True
            return False
        elif operator == OR:
            for pc in permission_classes:
                if not self.check_permission_class_requires_auth(pc):
                    return False
            return True
        elif operator == NOT:
            raise ValueError('NOT operator is not supported in permission_classes')
        else:
            return False
    
    def check_permission_class_requires_auth(self, permission_class):
        if isinstance(permission_class, OperandHolder):
            operator  = permission_class.operator_class
            op1_class = permission_class.op1_class
            op2_class = permission_class.op2_class
            permission_classes = [op1_class, op2_class]
            return self.check_permission_classes_requires_auth(permission_classes, operator)
        else:
            if issubclass(permission_class, (IsAuthenticated, RBACPermission)):
                return True
            if issubclass(permission_class, (AllowAny, )):
                return False
            if hasattr(permission_class, '__name__'):
                if 'Authenticated' in permission_class.__name__:
                    return True
                if permission_class.__name__.startswith('UserConfirmation'):
                    return True
            return False

    def check_view_func_requires_auth(self):
        if hasattr(self.view_func, '__wrapped__'):
            if hasattr(self.view_func, '__name__'):
                if 'login_required' in str(self.view_func):
                    return True
        return False


class CustomURLPattern:
    def __init__(self, raw, prefix='/'):
        self.raw = raw
        self.prefix = prefix
        self.full_path = f'{self.prefix}{self.raw.pattern}'
        self.view = CustomView(view_func=self.raw.callback)

    def __str__(self):
        s = f'{self.full_path} -> {self.view.view_path}'
        return s

    def __repr__(self):
        return self.__str__()


class ViewSchemaGenerator:

    def __init__(self):
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
        file_path = os.path.join(OUTPUT_FILE_DIR, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

if __name__ == '__main__':
    ViewSchemaGenerator().generate()