# -*- coding: utf-8 -*-
#
import re
from urllib.parse import unquote, urlsplit

import phonenumbers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _
from phonenumbers.phonenumberutil import NumberParseException
from rest_framework import serializers
from rest_framework.validators import (
    UniqueTogetherValidator, ValidationError
)

from common.utils.strings import no_special_chars

alphanumeric = RegexValidator(r'^[0-9a-zA-Z_@\-\.]*$', _('Special char not allowed'))

alphanumeric_re = re.compile(r'^[0-9a-zA-Z_@\-\.]*$')

alphanumeric_cn_re = re.compile(r'^[0-9a-zA-Z_@\-\.\u4E00-\u9FA5]*$')

alphanumeric_win_re = re.compile(r'^[0-9a-zA-Z_@#%&~\^\$\-\.\u4E00-\u9FA5]*$')


def validate_mcp_resource_url(value):
    try:
        uri = urlsplit(value)
        path = unquote(uri.path, encoding='utf-8', errors='strict')
        valid = (uri.scheme in ('http', 'https') and uri.hostname and uri.username is None and uri.password is None
                 and path.startswith('/') and not path.endswith('/') and not uri.query and not uri.fragment
                 and not re.search(r'%(?![0-9a-fA-F]{2})', uri.path) and '%' not in uri.netloc
                 and not any(ord(char) < 32 or ord(char) == 127 or char == '\\' for char in path)
                 and not any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in value)
                 and not any(char in value for char in '\\?#'))
        uri.port  # Validate an explicitly supplied port.
    except (ValueError, TypeError, UnicodeError):
        valid = False
    if not valid or len(value) > 512:
        raise DjangoValidationError(_(
            'Enter the exact HTTP or HTTPS MCP URL without credentials, a trailing slash, query or fragment.'
        ))
    return value


class ProjectUniqueValidator(UniqueTogetherValidator):
    def __call__(self, attrs, serializer):
        try:
            super().__call__(attrs, serializer)
        except ValidationError as e:
            errors = {}
            for field in self.fields:
                if field == "org_id":
                    continue
                errors[field] = _('This field must be unique.')
            raise ValidationError(errors)


class NoSpecialChars:
    def __call__(self, value):
        if not no_special_chars(value):
            raise serializers.ValidationError(
                _("Should not contains special characters")
            )


class PhoneValidator:
    message = _('The mobile phone number format is incorrect')

    def __call__(self, value):
        if not value:
            return

        try:
            phone = phonenumbers.parse(value, 'CN')
            valid = phonenumbers.is_valid_number(phone)
        except NumberParseException:
            valid = False

        if not valid:
            raise serializers.ValidationError(self.message)
