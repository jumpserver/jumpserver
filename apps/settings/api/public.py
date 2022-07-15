from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.conf import settings

from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from common.utils import get_logger, lazyproperty, get_object_or_none
from authentication.models import ConnectionToken
from orgs.utils import tmp_to_root_org
from common.permissions import IsValidUserOrConnectionToken

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

    def get_object(self):
        return {
            "XPACK_ENABLED": settings.XPACK_ENABLED,
            "INTERFACE": self.interface_setting
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



