from django.conf import settings
from django.shortcuts import reverse
from django.utils.translation import ugettext_lazy as _
from rest_framework import generics
from rest_framework.permissions import AllowAny

from common.permissions import IsValidUserOrConnectionToken
from common.utils import get_logger, lazyproperty, static_or_direct
from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from .. import serializers
from ..utils import get_interface_setting_or_default

logger = get_logger(__name__)

__all__ = ['PublicSettingApi', 'OpenPublicSettingApi']


class OpenPublicSettingApi(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @lazyproperty
    def interface_setting(self):
        return get_interface_setting_or_default()

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

    @lazyproperty
    def login_page_setting(self):
        auto_login_days = int(settings.SESSION_COOKIE_AGE / 3600 / 24) or 1
        if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE or auto_login_days < 1:
            auto_login_days = 0
        return {
            'AUTO_LOGIN_DAYS': auto_login_days,
            'FORGOT_PASSWORD_URL': settings.FORGOT_PASSWORD_URL,
            'AUTH_METHODS': self.get_support_auth_methods()
        }

    def get_object(self):
        return {
            "XPACK_ENABLED": settings.XPACK_ENABLED,
            "INTERFACE": self.interface_setting,
            "LOGIN_INFO": self.login_page_setting
        }


class PublicSettingApi(OpenPublicSettingApi):
    permission_classes = (IsValidUserOrConnectionToken,)
    serializer_class = serializers.PrivateSettingSerializer

    def get_object(self):
        values = super().get_object()
        values.update({
            "XPACK_LICENSE_IS_VALID": has_valid_xpack_license(),
            "XPACK_LICENSE_INFO": get_xpack_license_info(),
            "PASSWORD_RULE": {
                'SECURITY_PASSWORD_MIN_LENGTH': settings.SECURITY_PASSWORD_MIN_LENGTH,
                'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH': settings.SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH,
                'SECURITY_PASSWORD_UPPER_CASE': settings.SECURITY_PASSWORD_UPPER_CASE,
                'SECURITY_PASSWORD_LOWER_CASE': settings.SECURITY_PASSWORD_LOWER_CASE,
                'SECURITY_PASSWORD_NUMBER': settings.SECURITY_PASSWORD_NUMBER,
                'SECURITY_PASSWORD_SPECIAL_CHAR': settings.SECURITY_PASSWORD_SPECIAL_CHAR,
            },
        })

        serializer = self.serializer_class()
        field_names = list(serializer.fields.keys())
        for name in field_names:
            if name in values:
                continue
            # 提前把异常爆出来
            values[name] = getattr(settings, name)
        return values
