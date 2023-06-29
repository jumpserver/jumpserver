from django.conf import settings
from django.utils.translation import get_language
from rest_framework import generics
from rest_framework.permissions import AllowAny

from common.permissions import IsValidUserOrConnectionTokenOrSessionUser
from common.utils import get_logger, lazyproperty, reverse
from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from users.mixins import UserLoginContextMixin
from .. import serializers
from ..utils import get_interface_setting_or_default

logger = get_logger(__name__)

__all__ = ['PublicSettingApi', 'OpenPublicSettingApi']


class OpenPublicSettingApi(UserLoginContextMixin, generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @lazyproperty
    def interface_setting(self):
        return get_interface_setting_or_default()

    @staticmethod
    def get_not_request_profile_url():
        url_name = [
            'api-auth:forgot-password', 'api-auth:reset-password', 'users:user-profile',
            'api-auth:captcha-refresh', 'api-auth:login', 'api-common:flash-message',
            'api-settings:open-public-setting', 'api-auth:mfa-settings',
        ]
        return [reverse(url) for url in url_name]

    @lazyproperty
    def login_page_setting(self):
        auto_login_days = int(settings.SESSION_COOKIE_AGE / 3600 / 24) or 1
        if settings.SESSION_EXPIRE_AT_BROWSER_CLOSE_FORCE or auto_login_days < 1:
            auto_login_days = 0
        return {
            'AUTO_LOGIN_DAYS': auto_login_days,
            'FORGOT_PASSWORD_URL': settings.FORGOT_PASSWORD_URL,
            'AUTH_METHODS': self.get_support_auth_methods(),
            'LANGUAGE_CODE': get_language(),
            'NOT_PROFILE_URL_WHITELIST': self.get_not_request_profile_url()
        }

    def get_object(self):
        return {
            "XPACK_ENABLED": settings.XPACK_ENABLED,
            "INTERFACE": self.interface_setting,
            "LOGIN_INFO": self.login_page_setting
        }


class PublicSettingApi(OpenPublicSettingApi):
    permission_classes = (IsValidUserOrConnectionTokenOrSessionUser,)
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
