from django.conf import settings
from rest_framework import generics
from rest_framework.permissions import AllowAny

from authentication.permissions import IsValidUserOrConnectionToken
from common.const.choices import COUNTRY_CALLING_CODES
from common.utils import get_logger, lazyproperty
from common.utils.timezone import local_now
from .. import serializers
from ..utils import get_interface_setting_or_default

logger = get_logger(__name__)

__all__ = ['PublicSettingApi', 'OpenPublicSettingApi', 'ServerInfoApi']


class OpenPublicSettingApi(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @lazyproperty
    def interface_setting(self):
        return get_interface_setting_or_default()

    def get_object(self):
        return {
            "XPACK_ENABLED": settings.XPACK_ENABLED,
            "INTERFACE": self.interface_setting,
            "COUNTRY_CALLING_CODES": COUNTRY_CALLING_CODES
        }


class PublicSettingApi(OpenPublicSettingApi):
    permission_classes = (IsValidUserOrConnectionToken,)
    serializer_class = serializers.PrivateSettingSerializer

    def get_object(self):
        values = super().get_object()
        values.update({
            "XPACK_LICENSE_IS_VALID": settings.XPACK_LICENSE_IS_VALID,
            "XPACK_LICENSE_INFO": settings.XPACK_LICENSE_INFO,
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


class ServerInfoApi(generics.RetrieveAPIView):
    permission_classes = (IsValidUserOrConnectionToken,)
    serializer_class = serializers.ServerInfoSerializer

    def get_object(self):
        return {
            "CURRENT_TIME": local_now(),
        }
