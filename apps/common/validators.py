# -*- coding: utf-8 -*-
#
import re

import phonenumbers
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
        try:
            phone = phonenumbers.parse(value, 'CN')
            valid = phonenumbers.is_valid_number(phone)
        except NumberParseException:
            valid = False

        if not valid:
            raise serializers.ValidationError(self.message)
