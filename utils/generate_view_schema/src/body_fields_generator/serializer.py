from .base import FieldsGenerator
from common.utils import lazyproperty


__all__ = ['SerializerFieldsGenerator']


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
