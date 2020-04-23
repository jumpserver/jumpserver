# -*- coding: utf-8 -*-
#
import re
from urllib.parse import urljoin
from functools import partial
from werkzeug.local import LocalProxy
from common.local import thread_local


def set_current_request(request):
    setattr(thread_local, 'current_request', request)


def _find(attr):
    return getattr(thread_local, attr, None)


def get_current_request():
    return _find('current_request')


def is_absolute_uri(uri):
    """ 判断一个uri是否是绝对地址 """
    if not isinstance(uri, str):
        return False

    result = re.match(r'^http[s]?://.*', uri)
    if result is None:
        return False

    return True


def build_absolute_uri(base, uri):
    """ 构建绝对uri地址 """
    if uri is None:
        return None

    if is_absolute_uri(uri):
        return uri

    return urljoin(base, uri)


current_request = LocalProxy(partial(_find, 'current_request'))
