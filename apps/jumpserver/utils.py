# -*- coding: utf-8 -*-
#
from functools import partial
from werkzeug.local import LocalProxy

from django.conf import settings
from common.local import thread_local


def set_current_request(request):
    setattr(thread_local, 'current_request', request)


def _find(attr):
    return getattr(thread_local, attr, None)


def get_current_request():
    return _find('current_request')


def has_valid_xpack_license():
    if not settings.XPACK_ENABLED:
        return False
    from xpack.plugins.license.models import License
    return License.has_valid_license()


current_request = LocalProxy(partial(_find, 'current_request'))
