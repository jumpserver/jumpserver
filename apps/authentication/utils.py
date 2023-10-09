# -*- coding: utf-8 -*-
#
import ipaddress
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from audits.const import DEFAULT_CITY
from audits.models import UserLoginLog
from common.utils import get_logger
from common.utils import validate_ip, get_ip_city, get_request_ip, is_same_city
from common.utils.ip.geoip import get_ip_city_names_by_geoip
from .notifications import DifferentCityLoginMessage

logger = get_logger(__file__)


def check_different_city_login_if_need(user, request):
    if not settings.SECURITY_CHECK_DIFFERENT_CITY_LOGIN:
        return

    ip = get_request_ip(request) or '0.0.0.0'

    city_white = [_('LAN'), 'LAN']
    is_private = ipaddress.ip_address(ip).is_private
    if is_private:
        return

    last_user_login = UserLoginLog.objects.exclude(
        city__in=city_white
    ).filter(username=user.username, status=True).first()
    if not last_user_login:
        return

    last_city = last_user_login.city

    # 获取所有语言的 ip 城市名
    city_names = None
    if ip and validate_ip(ip):
        city_names = get_ip_city_names_by_geoip(ip)
        city_names = list(city_names.values())
    city_names = city_names or [DEFAULT_CITY]

    if not is_same_city(city=last_city, city_names=city_names):
        return

    city = get_ip_city(ip)
    DifferentCityLoginMessage(user, ip, city).publish_async()


def build_absolute_uri(request, path=None):
    """ Build absolute redirect """
    if path is None:
        path = '/'
    site_url = urlparse(settings.SITE_URL)
    scheme = site_url.scheme or request.scheme
    host = request.get_host()
    url = f'{scheme}://{host}'
    redirect_uri = urljoin(url, path)
    return redirect_uri


def build_absolute_uri_for_oidc(request, path=None):
    """ Build absolute redirect uri for OIDC """
    if path is None:
        path = '/'
    if settings.BASE_SITE_URL:
        # OIDC 专用配置项
        redirect_uri = urljoin(settings.BASE_SITE_URL, path)
        return redirect_uri
    return build_absolute_uri(request, path=path)
