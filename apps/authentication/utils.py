# -*- coding: utf-8 -*-
#
import ipaddress
from datetime import timedelta
from urllib.parse import urljoin, urlparse

from django.conf import settings
from django.shortcuts import reverse
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from audits.models import UserLoginLog
from assets.const import Protocol
from common.utils import get_ip_city, get_request_ip
from common.utils import get_logger, get_object_or_none
from common.utils import static_or_direct
from common.utils.http import is_true
from users.models import User
from .notifications import DifferentCityLoginMessage

logger = get_logger(__file__)


def should_use_oracle_sysdba(connect_options, protocol, asset=None):
    if protocol != Protocol.oracle:
        return False
    if is_true((connect_options or {}).get('use_sysdba', False)):
        return True
    if asset is None:
        return False
    # A default false submitted by a client must not disable the platform role.
    oracle = asset.platform.protocols.filter(name=Protocol.oracle).first()
    return oracle is not None and is_true((oracle.setting or {}).get('sysdba', False))


def get_effective_connect_options(connect_options, protocol, asset=None):
    options = dict(connect_options or {})
    if protocol != Protocol.rdp:
        options.pop('rdp_security', None)
    elif 'rdp_security' in options and options['rdp_security'] not in (
        'default', 'any', 'rdp', 'tls', 'nla',
    ):
        raise ValidationError({
            'connect_options': {'rdp_security': _('Invalid RDP security layer.')},
        })
    if protocol != Protocol.oracle:
        options.pop('use_sysdba', None)
        return options
    options['use_sysdba'] = should_use_oracle_sysdba(options, protocol, asset)
    return options


def check_different_city_login_if_need(user, request):
    if not settings.SECURITY_CHECK_DIFFERENT_CITY_LOGIN:
        return

    ip = get_request_ip(request) or '0.0.0.0'
    city_white = [_('LAN'), 'LAN']
    is_private = ipaddress.ip_address(ip).is_private
    if is_private:
        return
    usernames = [user.username, f"{user.name}({user.username})"]
    login_logs = UserLoginLog.objects.filter(
        username__in=usernames, status=True,
    ).exclude(city__in=city_white)
    if not login_logs.exists():
        return

    city = get_ip_city(ip)
    if login_logs.filter(
        datetime__gte=timezone.now() - timedelta(days=7),
        city=city,
    ).exists():
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
            'url': reverse('authentication:openid:login'),
            'logo': static('img/login_oidc_logo.png'),
            'auto_redirect': True  # 是否支持自动重定向
        },
        {
            'name': 'CAS',
            'enabled': settings.AUTH_CAS,
            'url': reverse('authentication:cas:cas-login'),
            'logo': static('img/login_cas_logo.png'),
            'auto_redirect': True
        },
        {
            'name': 'SAML2',
            'enabled': settings.AUTH_SAML2,
            'url': reverse('authentication:saml2:saml2-login'),
            'logo': static('img/login_saml2_logo.png'),
            'auto_redirect': True
        },
        {
            'name': settings.AUTH_OAUTH2_PROVIDER,
            'enabled': settings.AUTH_OAUTH2,
            'url': reverse('authentication:oauth2:login'),
            'logo': static_or_direct(settings.AUTH_OAUTH2_LOGO_PATH),
            'auto_redirect': True
        },
        {
            'name': _('WeCom'),
            'enabled': settings.AUTH_WECOM,
            'url': reverse('authentication:wecom-qr-login'),
            'logo': static('img/login_wecom_logo.png'),
        },
        {
            'name': _('DingTalk'),
            'enabled': settings.AUTH_DINGTALK,
            'url': reverse('authentication:dingtalk-qr-login'),
            'logo': static('img/login_dingtalk_logo.png')
        },
        {
            'name': _('FeiShu'),
            'enabled': settings.AUTH_FEISHU,
            'url': reverse('authentication:feishu-qr-login'),
            'logo': static('img/login_feishu_logo.png')
        },
        {
            'name': 'Lark',
            'enabled': settings.AUTH_LARK,
            'url': reverse('authentication:lark-qr-login'),
            'logo': static('img/login_lark_logo.png')
        },
        {
            'name': _('Slack'),
            'enabled': settings.AUTH_SLACK,
            'url': reverse('authentication:slack-qr-login'),
            'logo': static('img/login_slack_logo.png')
        },
        {
            'name': _("Passkey"),
            'enabled': settings.AUTH_PASSKEY,
            'url': reverse('api-auth:passkey-login'),
            'logo': static('img/login_passkey.png')
        },
        {
            'name': _('UKey'),
            'enabled': settings.AUTH_UKEY,
            'url': reverse('authentication:ukey:ukey-login'),
            'logo': static('img/login_ukey.png')
        }
    ]
