# -*- coding: utf-8 -*-
#
import os
import ipaddress

import geoip2.database
from geoip2.errors import GeoIP2Error
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

__all__ = ['get_ip_city']
reader = None


def get_ip_city(ip):
    if not ip or '.' not in ip or not isinstance(ip, str):
        return _("Invalid ip")
    if ':' in ip:
        return 'IPv6'
    global reader
    if reader is None:
        path = os.path.join(os.path.dirname(__file__), 'GeoLite2-City.mmdb')
        reader = geoip2.database.Reader(path)

    try:
        is_private = ipaddress.ip_address(ip.strip()).is_private
        if is_private:
            return _('LAN')
    except ValueError:
        return _("Invalid ip")

    try:
        response = reader.city(ip)
    except GeoIP2Error:
        return _("Unknown ip")

    names = response.city.names
    if not names:
        names = response.country.names

    if 'en' in settings.LANGUAGE_CODE and 'en' in names:
        return names['en']
    elif 'zh-CN' in names:
        return names['zh-CN']
    return _("Unknown ip")

