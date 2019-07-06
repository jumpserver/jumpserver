#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from django.utils import timezone
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from common.utils import validate_ssh_private_key


__all__ = [
    'init_model', 'generate_fake', 'private_key_validator', 'Connectivity',
]


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


class Connectivity:
    UNREACHABLE, REACHABLE, UNKNOWN = range(0, 3)
    CONNECTIVITY_CHOICES = (
        (UNREACHABLE, _("Unreachable")),
        (REACHABLE, _('Reachable')),
        (UNKNOWN, _("Unknown")),
    )

    status = UNKNOWN
    datetime = timezone.now()

    def __init__(self, status, datetime):
        self.status = status
        self.datetime = datetime

    def display(self):
        return dict(self.__class__.CONNECTIVITY_CHOICES).get(self.status)

    def is_reachable(self):
        return self.status == self.REACHABLE

    def is_unreachable(self):
        return self.status == self.UNREACHABLE

    def is_unknown(self):
        return self.status == self.UNKNOWN

    @classmethod
    def unreachable(cls):
        return cls(cls.UNREACHABLE, timezone.now())

    @classmethod
    def reachable(cls):
        return cls(cls.REACHABLE, timezone.now())

    @classmethod
    def unknown(cls):
        return cls(cls.UNKNOWN, timezone.now())

    @classmethod
    def set(cls, key, value, ttl=0):
        cache.set(key, value, ttl)

    @classmethod
    def get(cls, key):
        value = cache.get(key, cls.unknown())
        if not isinstance(value, cls):
            value = cls.unknown()
        return value

    @classmethod
    def set_unreachable(cls, key, ttl=0):
        cls.set(key, cls.unreachable(), ttl)

    @classmethod
    def set_reachable(cls, key, ttl=0):
        cls.set(key, cls.reachable(), ttl)

    def __eq__(self, other):
        return self.status == other.status

    def __gt__(self, other):
        return self.status > other.status

    def __lt__(self, other):
        return not self.__gt__(other)

    def __str__(self):
        return self.display()
