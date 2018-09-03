# -*- coding: utf-8 -*-
#

from functools import partial

from common.utils import LocalProxy

try:
    from threading import local
except ImportError:
    from django.utils._threading_local import local

_thread_locals = local()


def set_current_request(request):
    setattr(_thread_locals, 'current_request', request)


def _find(attr):
    return getattr(_thread_locals, attr, None)


def get_current_request():
    return _find('current_request')


current_request = LocalProxy(partial(_find, 'current_request'))

