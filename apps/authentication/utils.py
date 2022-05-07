# -*- coding: utf-8 -*-
#

from django.conf import settings

from common.utils import validate_ip, get_ip_city, get_request_ip
from common.utils import get_logger
from audits.models import UserLoginLog
from audits.const import DEFAULT_CITY
from .notifications import DifferentCityLoginMessage

logger = get_logger(__file__)


def check_different_city_login_if_need(user, request):
    if not settings.SECURITY_CHECK_DIFFERENT_CITY_LOGIN:
        return

    ip = get_request_ip(request) or '0.0.0.0'
    if not (ip and validate_ip(ip)):
        city = DEFAULT_CITY
    else:
        city = get_ip_city(ip) or DEFAULT_CITY

    city_white = ['LAN', ]
    if city not in city_white:
        last_user_login = UserLoginLog.objects.exclude(city__in=city_white) \
            .filter(username=user.username, status=True).first()

        if last_user_login and last_user_login.city != city:
            DifferentCityLoginMessage(user, ip, city).publish_async()
