from django.conf import settings
from django.shortcuts import reverse
from django.utils.translation import ugettext_lazy as _

from common.utils import static_or_direct


class UserLoginContextMixin:
    @staticmethod
    def get_support_auth_methods():
        auth_methods = [
            {
                'name': 'OpenID',
                'enabled': settings.AUTH_OPENID,
                'url': reverse('authentication:openid:login'),
                'logo': static_or_direct('img/login_oidc_logo.png'),
                'auto_redirect': True  # 是否支持自动重定向
            },
            {
                'name': 'CAS',
                'enabled': settings.AUTH_CAS,
                'url': reverse('authentication:cas:cas-login'),
                'logo': static_or_direct('img/login_cas_logo.png'),
                'auto_redirect': True
            },
            {
                'name': 'SAML2',
                'enabled': settings.AUTH_SAML2,
                'url': reverse('authentication:saml2:saml2-login'),
                'logo': static_or_direct('img/login_saml2_logo.png'),
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
                'logo': static_or_direct('img/login_wecom_logo.png'),
            },
            {
                'name': _('DingTalk'),
                'enabled': settings.AUTH_DINGTALK,
                'url': reverse('authentication:dingtalk-qr-login'),
                'logo': static_or_direct('img/login_dingtalk_logo.png')
            },
            {
                'name': _('FeiShu'),
                'enabled': settings.AUTH_FEISHU,
                'url': reverse('authentication:feishu-qr-login'),
                'logo': static_or_direct('img/login_feishu_logo.png')
            }
        ]
        return [method for method in auth_methods if method['enabled']]

    @staticmethod
    def get_support_languages():
        return [
            {
                'title': '中文(简体)',
                'code': 'zh-hans'
            },
            {
                'title': 'English',
                'code': 'en'
            },
            {
                'title': '日本語',
                'code': 'ja'
            }
        ]
