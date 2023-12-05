# -*- coding: utf-8 -*-
#
import re

from django.conf import settings
from django.db import models
from django.db.models.signals import post_save, pre_save
from django.shortcuts import reverse as dj_reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

UUID_PATTERN = re.compile(r'[0-9a-zA-Z\-]{36}')


def reverse(
        view_name, urlconf=None, args=None, kwargs=None,
        current_app=None, external=False, api_to_ui=False,
        is_console=False, is_audit=False, is_workbench=False
):
    url = dj_reverse(view_name, urlconf=urlconf, args=args,
                     kwargs=kwargs, current_app=current_app)

    if external:
        site_url = settings.SITE_URL
        url = site_url.strip('/') + url
    if api_to_ui:
        replace_str = 'ui/#'
        if is_console:
            replace_str += '/console'
        elif is_audit:
            replace_str += '/audit'
        elif is_workbench:
            replace_str += '/workbench'

        url = url.replace('api/v1', replace_str).rstrip('/')
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
    return timezone.now() + timezone.timedelta(days=365 * years)


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


def get_log_keep_day(s, defaults=200):
    try:
        days = int(getattr(settings, s))
    except ValueError:
        days = defaults
    return days


def bulk_create_with_signal(cls: models.Model, items, **kwargs):
    for i in items:
        pre_save.send(sender=cls, instance=i)
    result = cls.objects.bulk_create(items, **kwargs)
    for i in items:
        post_save.send(sender=cls, instance=i, created=True)
    return result


def get_request_os(request):
    """获取请求的操作系统"""
    agent = request.META.get('HTTP_USER_AGENT', '').lower()

    if 'windows' in agent:
        return 'windows'
    elif 'mac' in agent:
        return 'mac'
    elif 'linux' in agent:
        return 'linux'
    else:
        return 'unknown'


def safe_next_url(next_url, request=None):
    safe_hosts = [*settings.ALLOWED_HOSTS]
    if request:
        safe_hosts.append(request.get_host())
    if not next_url or not url_has_allowed_host_and_scheme(next_url, safe_hosts):
        next_url = '/'
    return next_url
