#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from common.utils import validate_ssh_private_key

__all__ = [
    'private_key_validator',
]


def private_key_validator(value):
    if not validate_ssh_private_key(value):
        raise ValidationError(
            _('%(value)s is not an even number'),
            params={'value': value},
        )
