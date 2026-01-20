from django import forms
from django.contrib.auth.mixins import LoginRequiredMixin

from .base import BaseExtractor
from .django_view import DjangoViewExtractor
from routing.discover import Route
from routing.resolver import View
from schema.endpoint import QueryField, BodyField


class DjangoFormViewExtractor(DjangoViewExtractor):

    def extract_body_fields(self, method: str):
        form_class = self.get_form_class()
        if not form_class:
            return []
        form: forms.Form = form_class()
        body_fields = []
        for field_name, field in form.fields.items():
            field: forms.Field
            body_field = BodyField(
                name=field_name,
                field_type=self.get_field_type(field),
                required=field.required,
                description=str(field.help_text) or '',
            )
            body_fields.append(body_field)
        return body_fields
    
    def get_field_type(self, form_field):
        field_type_mapping = {
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
        for field_type, json_type in field_type_mapping.items():
            if issubclass(type(form_field), field_type):
                return json_type
        return 'string'
        # raise ValueError(f"Unsupported form field type: {type(form_field)}")

    def get_form_class(self):
        view = self.view
        form_class = getattr(view.view_class, 'form_class', None)
        if form_class:
            return form_class

        view_instance = view.view_class(request=self.fake_request)

        if hasattr(view_instance, 'get_form_class_comprehensive'):
            form_class = view_instance.get_form_class_comprehensive()
            return form_class

        if hasattr(view_instance, 'get_form_class'):
            form_class = view_instance.get_form_class()
            return form_class
