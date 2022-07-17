# -*- coding: utf-8 -*-
#
import os
import ipaddress

import geoip2.database
from geoip2.errors import GeoIP2Error
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

__all__ = ['get_ip_city_by_geoip']
reader = None


def get_ip_city_by_geoip(ip):
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
        return _("Unknown")

    city_names = response.city.names or {}
    lang = settings.LANGUAGE_CODE[:2]
    if lang == 'zh':
        lang = 'zh-CN'
    city = city_names.get(lang, _("Unknown"))
    return city


