from rest_framework import serializers
from .base import BaseExtractor
from .django_view import DjangoViewExtractor
from schema.endpoint import BodyField

class DrfAPIViewExtractor(DjangoViewExtractor):

    def extract_body_fields(self, method: str) -> list:
        serializer_class = self.get_serializer_class()
        if not serializer_class:
            return []
        serializer = serializer_class()
        fields = self.get_serializer_fields(serializer)
        body_fields = self.wrap_as_body_fields(fields)
        return body_fields
    
    def wrap_as_body_fields(self, serializer_fields):
        if not hasattr(serializer_fields, 'items'):
            return []
        body_fields = []
        for field_name, field in serializer_fields.items():
            field: serializers.Field
            body_field = BodyField(
                name=field_name,
                field_type=self.get_field_type(field),
                required=field.required,
                description=str(field.help_text) or ''
            )
            if hasattr(field, 'child'):
                _body_fields = self.wrap_as_body_fields(field.child)
                body_field.extend_child(_body_fields)

            body_fields.append(body_field)
        return body_fields
    
    def get_field_type(self, serializer_field):
        if hasattr(serializer_field, 'child'):
            return 'object'

        field_type_mapping = {
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
        for field_type, json_type in field_type_mapping.items():
            if issubclass(type(serializer_field), field_type):
                return json_type
        return 'string'
    
    def get_serializer_fields(self, serializer):
        try:
            fields = serializer.fields
        except Exception as e:
            fields = getattr(self.view.view_class, '_declared_fields', {})
        return fields

    def get_serializer_class(self):
        serializer_class = getattr(self.view.view_class, 'serializer_class', None)
        if serializer_class:
            return serializer_class
        
        view_instance = self.view.view_class(request=self.fake_request)
        if hasattr(view_instance, 'get_serializer_class'):
            try:
                serializer_class = view_instance.get_serializer_class()
            except Exception as e:
                serializer_class = None
            return serializer_class
