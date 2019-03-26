# -*- coding: utf-8 -*-
#
from django.utils.translation import ugettext as _
from common.utils import get_ip_city, validate_ip


def write_login_log(*args, **kwargs):
    from audits.models import UserLoginLog
    default_city = _("Unknown")
    ip = kwargs.get('ip', '')
    if not (ip and validate_ip(ip)):
        ip = ip[:15]
        city = default_city
    else:
        city = get_ip_city(ip) or default_city
    kwargs.update({'ip': ip, 'city': city})
    UserLoginLog.objects.create(**kwargs)

