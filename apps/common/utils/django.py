# -*- coding: utf-8 -*-
#
import re
from django.shortcuts import reverse as dj_reverse
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


def get_command_storage_setting():
    default = settings.DEFAULT_TERMINAL_COMMAND_STORAGE
    value = settings.TERMINAL_COMMAND_STORAGE
    if not value:
        return default
    value.update(default)
    return value


def get_replay_storage_setting():
    default = settings.DEFAULT_TERMINAL_REPLAY_STORAGE
    value = settings.TERMINAL_REPLAY_STORAGE
    if not value:
        return default
    value.update(default)
    return value
