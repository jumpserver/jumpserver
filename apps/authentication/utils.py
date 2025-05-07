# -*- coding: utf-8 -*-
#
import ipaddress
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils.translation import gettext_lazy as _

from audits.models import UserLoginLog
from common.utils import get_ip_city, get_request_ip
from common.utils import get_logger, get_object_or_none
from common.utils import static_or_direct
from users.models import User
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
    usernames = [user.username, f"{user.name}({user.username})"]
    last_user_login = UserLoginLog.objects.exclude(
        city__in=city_white
    ).filter(username__in=usernames, status=True).first()
    if not last_user_login:
        return

    city = get_ip_city(ip)
    last_cities = UserLoginLog.objects.filter(
        datetime__gte=datetime.now() - timedelta(days=7),
        username__in=usernames,
        status=True
    ).exclude(city__in=city_white).values_list('city', flat=True).distinct()

    if city in last_cities:
        return

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


def check_user_property_is_correct(username, **properties):
    user = get_object_or_none(User, username=username)
    for attr, value in properties.items():
        if getattr(user, attr, None) != value:
            user = None
            break
    return user


def get_auth_methods():
    return [
        {
            'name': 'OpenID',
            'enabled': settings.AUTH_OPENID,
            'url': f"{reverse('authentication:openid:login')}",
            'logo': static('img/login_oidc_logo.png'),
            'auto_redirect': True  # 是否支持自动重定向
        },
        {
            'name': 'CAS',
            'enabled': settings.AUTH_CAS,
            'url': f"{reverse('authentication:cas:cas-login')}",
            'logo': static('img/login_cas_logo.png'),
            'auto_redirect': True
        },
        {
            'name': 'SAML2',
            'enabled': settings.AUTH_SAML2,
            'url': f"{reverse('authentication:saml2:saml2-login')}",
            'logo': static('img/login_saml2_logo.png'),
            'auto_redirect': True
        },
        {
            'name': settings.AUTH_OAUTH2_PROVIDER,
            'enabled': settings.AUTH_OAUTH2,
            'url': f"{reverse('authentication:oauth2:login')}",
            'logo': static_or_direct(settings.AUTH_OAUTH2_LOGO_PATH),
            'auto_redirect': True
        },
        {
            'name': _('WeCom'),
            'enabled': settings.AUTH_WECOM,
            'url': f"{reverse('authentication:wecom-qr-login')}",
            'logo': static('img/login_wecom_logo.png'),
        },
        {
            'name': _('DingTalk'),
            'enabled': settings.AUTH_DINGTALK,
            'url': f"{reverse('authentication:dingtalk-qr-login')}",
            'logo': static('img/login_dingtalk_logo.png')
        },
        {
            'name': _('FeiShu'),
            'enabled': settings.AUTH_FEISHU,
            'url': f"{reverse('authentication:feishu-qr-login')}",
            'logo': static('img/login_feishu_logo.png')
        },
        {
            'name': 'Lark',
            'enabled': settings.AUTH_LARK,
            'url': f"{reverse('authentication:lark-qr-login')}",
            'logo': static('img/login_lark_logo.png')
        },
        {
            'name': _('Slack'),
            'enabled': settings.AUTH_SLACK,
            'url': f"{reverse('authentication:slack-qr-login')}",
            'logo': static('img/login_slack_logo.png')
        },
        {
            'name': _("Passkey"),
            'enabled': settings.AUTH_PASSKEY,
            'url': f"{reverse('api-auth:passkey-login')}",
            'logo': static('img/login_passkey.png')
        }
    ]
