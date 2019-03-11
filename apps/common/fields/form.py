# -*- coding: utf-8 -*-
#
import json

from django import forms
from django.utils import six
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _
from ..utils import get_signer

signer = get_signer()

__all__ = [
    'FormDictField', 'FormEncryptCharField', 'FormEncryptDictField',
    'FormEncryptMixin',
]


class FormDictField(forms.Field):
    widget = forms.Textarea

    def to_python(self, value):
        """Returns a Python boolean object."""
        # Explicitly check for the string 'False', which is what a hidden field
        # will submit for False. Also check for '0', since this is what
        # RadioSelect will provide. Because bool("True") == bool('1') == True,
        # we don't need to handle that explicitly.
        if isinstance(value, six.string_types):
            value = value.replace("'", '"')
            try:
                value = json.loads(value)
                return value
            except json.JSONDecodeError:
                return ValidationError(_("Not a valid json"))
        else:
            return ValidationError(_("Not a string type"))

    def validate(self, value):
        if isinstance(value, ValidationError):
            raise value
        if not value and self.required:
            raise ValidationError(self.error_messages['required'], code='required')

    def has_changed(self, initial, data):
        # Sometimes data or initial may be a string equivalent of a boolean
        # so we should run it through to_python first to get a boolean value
        return self.to_python(initial) != self.to_python(data)


class FormEncryptMixin:
    pass


class FormEncryptCharField(FormEncryptMixin, forms.CharField):
    pass


class FormEncryptDictField(FormEncryptMixin, FormDictField):
    pass




