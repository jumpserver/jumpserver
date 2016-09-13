# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
from itertools import chain
import string

from django.shortcuts import reverse as dj_reverse
from django.conf import settings
from django.core import signing
from django.utils import timezone


def reverse(viewname, urlconf=None, args=None, kwargs=None, current_app=None, external=False):
    url = dj_reverse(viewname, urlconf=urlconf, args=args, kwargs=kwargs, current_app=current_app)

    if external:
        url = settings.SITE_URL.strip('/') + url
    return url


def get_object_or_none(model, **kwargs):
    try:
        obj = model.objects.get(**kwargs)
    except model.DoesNotExist:
        obj = None
    return obj


def encrypt(*args, **kwargs):
    return signing.dumps(*args, **kwargs)


def decrypt(*args, **kwargs):
    return signing.loads(*args, **kwargs)


def date_expired_default():
    try:
        years = int(settings.CONFIG.DEFAULT_EXPIRED_YEARS)
    except TypeError:
        years = 70

    return timezone.now() + timezone.timedelta(days=365 * years)


def combine_seq(s1, s2, callback=None):
    for s in (s1, s2):
        if not hasattr(s, '__iter__'):
            return []

    seq = chain(s1, s2)
    if callback:
        seq = map(callback, seq)

    return seq


def search_object_attr(obj, value='', attr_list=None, ignore_case=False):
    try:
        object_attr = obj.__dict__
    except AttributeError:
        return False

    if not isinstance(value, str):
        return False

    if value == '':
        return True

    if attr_list is not None:
        for attr in attr_list:
            object_attr.pop(attr)

    print(value)
    print(object_attr)
    if ignore_case:
        if value.lower() in map(string.lower, filter(lambda x: isinstance(x, (str, unicode)), object_attr.values())):
            return True
    else:
        if value in object_attr.values():
            return True
    return False


