# -*- coding: utf-8 -*-
#
import json

from django import forms
from django.utils import six
from django.core.exceptions import ValidationError


class DictField(forms.Field):
    widget = forms.Textarea

    def to_python(self, value):
        """Returns a Python boolean object."""
        # Explicitly check for the string 'False', which is what a hidden field
        # will submit for False. Also check for '0', since this is what
        # RadioSelect will provide. Because bool("True") == bool('1') == True,
        # we don't need to handle that explicitly.
        if isinstance(value, six.string_types):
            try:
                print(value)
                value = json.loads(value)
                return value
            except json.JSONDecodeError:
                pass
        value = {}
        return value

    def validate(self, value):
        print(value)
        if not value and self.required:
            raise ValidationError(self.error_messages['required'], code='required')

    def has_changed(self, initial, data):
        # Sometimes data or initial may be a string equivalent of a boolean
        # so we should run it through to_python first to get a boolean value
        return self.to_python(initial) != self.to_python(data)
