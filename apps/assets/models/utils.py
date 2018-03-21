#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.core.exceptions import ValidationError
from common.utils import validate_ssh_private_key


__all__ = ['init_model', 'generate_fake']


def init_model():
    from . import SystemUser, AdminUser, Asset
    for cls in [SystemUser, AdminUser, Asset]:
        if hasattr(cls, 'initial'):
            cls.initial()


def generate_fake():
    from . import SystemUser, AdminUser,  Asset
    for cls in [SystemUser, AdminUser, Asset]:
        if hasattr(cls, 'generate_fake'):
            cls.generate_fake()


def private_key_validator(value):
    if not validate_ssh_private_key(value):
        raise ValidationError(
            _('%(value)s is not an even number'),
            params={'value': value},
        )


if __name__ == '__main__':
    pass
