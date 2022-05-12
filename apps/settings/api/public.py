from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings

from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from common.utils import get_logger
from .. import serializers
from ..utils import get_interface_setting

logger = get_logger(__name__)

__all__ = ['PublicSettingApi', 'OpenPublicSettingApi']


class OpenPublicSettingApi(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @staticmethod
    def get_logo_urls():
        interface = get_interface_setting()
        keys = ['logo_logout', 'logo_index', 'login_image', 'favicon']
        return {k: interface[k] for k in keys}

    @staticmethod
    def get_login_title():
        interface = get_interface_setting()
        return interface['login_title']

    def get_object(self):
        return {
            "XPACK_ENABLED": settings.XPACK_ENABLED,
            "LOGIN_TITLE": self.get_login_title(),
            "LOGO_URLS": self.get_logo_urls(),
        }


class PublicSettingApi(OpenPublicSettingApi):
    permission_classes = (IsAuthenticated,)
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



