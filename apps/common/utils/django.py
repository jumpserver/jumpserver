# -*- coding: utf-8 -*-
#
import re
from django.shortcuts import reverse as dj_reverse
from django.db.models import Subquery, QuerySet
from django.conf import settings
from django.utils import timezone


UUID_PATTERN = re.compile(r'[0-9a-zA-Z\-]{36}')


def reverse(view_name, urlconf=None, args=None, kwargs=None,
            current_app=None, external=False):
    url = dj_reverse(view_name, urlconf=urlconf, args=args,
                     kwargs=kwargs, current_app=current_app)

    if external:
        site_url = settings.SITE_URL
        url = site_url.strip('/') + url
    return url


def get_object_or_none(model, **kwargs):
    try:
        obj = model.objects.get(**kwargs)
    except model.DoesNotExist:
        return None
    return obj


def date_expired_default():
    try:
        years = int(settings.DEFAULT_EXPIRED_YEARS)
    except TypeError:
        years = 70
    return timezone.now() + timezone.timedelta(days=365*years)


def union_queryset(*args, base_queryset=None):
    if len(args) == 1:
        return args[0]
    elif len(args) == 0:
        raise ValueError("args is empty")
    args = [q.order_by() for q in args]
    sub_query = args[0].union(*args[1:])
    queryset_id = list(sub_query.values_list('id', flat=True))
    if not base_queryset:
        base_queryset = args[0].model.objects
    queryset = base_queryset.filter(id__in=queryset_id)
    return queryset
