from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.conf import settings

from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from common.utils import get_logger
from .. import serializers
from ..utils import get_interface_setting

logger = get_logger(__name__)

__all__ = ['AuthenticatedSettingApi']


class AuthenticatedSettingApi(generics.RetrieveAPIView):
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
        instance = {
            "data": {
                # XPACK
                "XPACK_ENABLED": settings.XPACK_ENABLED,
                # Performance
                "LOGIN_TITLE": self.get_login_title(),
                "LOGO_URLS": self.get_logo_urls(),
            }
        }
        return instance
