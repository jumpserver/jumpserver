
from common.utils import lazyproperty
from .base import FieldsGenerator

__all__ = ['FormFieldsGenerator']


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

