# -*- coding: utf-8 -*-
#
from functools import partial
from werkzeug.local import LocalProxy
from datetime import datetime

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


def get_xpack_license_info() -> dict:
    if has_valid_xpack_license():
        from xpack.plugins.license.models import License
        info = License.get_license_detail()
        corporation = info.get('corporation', '')
    else:
        current_year = datetime.now().year
        corporation = f'Copyright - FIT2CLOUD 飞致云 © 2014-{current_year}'
    info = {
        'corporation': corporation
    }
    return info


current_request = LocalProxy(partial(_find, 'current_request'))
