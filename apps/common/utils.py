# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.shortcuts import reverse as dj_reverse
from django.conf import settings
from django.core import signing


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

