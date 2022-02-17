from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.conf import settings

from jumpserver.utils import has_valid_xpack_license, get_xpack_license_info
from common.utils import get_logger
from .. import serializers
from ..utils import get_interface_setting

logger = get_logger(__name__)

__all__ = ['PublicSettingApi']


class PublicSettingApi(generics.RetrieveAPIView):
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
                "WINDOWS_SKIP_ALL_MANUAL_PASSWORD": settings.WINDOWS_SKIP_ALL_MANUAL_PASSWORD,
                "SECURITY_MAX_IDLE_TIME": settings.SECURITY_MAX_IDLE_TIME,
                "XPACK_ENABLED": settings.XPACK_ENABLED,
                "SECURITY_VIEW_AUTH_NEED_MFA": settings.SECURITY_VIEW_AUTH_NEED_MFA,
                "SECURITY_MFA_VERIFY_TTL": settings.SECURITY_MFA_VERIFY_TTL,
                "OLD_PASSWORD_HISTORY_LIMIT_COUNT": settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT,
                "SECURITY_COMMAND_EXECUTION": settings.SECURITY_COMMAND_EXECUTION,
                "SECURITY_PASSWORD_EXPIRATION_TIME": settings.SECURITY_PASSWORD_EXPIRATION_TIME,
                "SECURITY_LUNA_REMEMBER_AUTH": settings.SECURITY_LUNA_REMEMBER_AUTH,
                "XPACK_LICENSE_IS_VALID": has_valid_xpack_license(),
                "XPACK_LICENSE_INFO": get_xpack_license_info(),
                "LOGIN_TITLE": self.get_login_title(),
                "LOGO_URLS": self.get_logo_urls(),
                "TICKETS_ENABLED": settings.TICKETS_ENABLED,
                "PASSWORD_RULE": {
                    'SECURITY_PASSWORD_MIN_LENGTH': settings.SECURITY_PASSWORD_MIN_LENGTH,
                    'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH': settings.SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH,
                    'SECURITY_PASSWORD_UPPER_CASE': settings.SECURITY_PASSWORD_UPPER_CASE,
                    'SECURITY_PASSWORD_LOWER_CASE': settings.SECURITY_PASSWORD_LOWER_CASE,
                    'SECURITY_PASSWORD_NUMBER': settings.SECURITY_PASSWORD_NUMBER,
                    'SECURITY_PASSWORD_SPECIAL_CHAR': settings.SECURITY_PASSWORD_SPECIAL_CHAR,
                },
                "AUTH_WECOM": settings.AUTH_WECOM,
                "AUTH_DINGTALK": settings.AUTH_DINGTALK,
                "AUTH_FEISHU": settings.AUTH_FEISHU,
                'SECURITY_WATERMARK_ENABLED': settings.SECURITY_WATERMARK_ENABLED,
                'SECURITY_SESSION_SHARE': settings.SECURITY_SESSION_SHARE,
                "XRDP_ENABLED": settings.XRDP_ENABLED,
                "ANNOUNCEMENT_ENABLED": settings.ANNOUNCEMENT_ENABLED,
                "ANNOUNCEMENT": settings.ANNOUNCEMENT,
                "HELP_DOCUMENT_URL": settings.HELP_DOCUMENT_URL,
                "HELP_SUPPORT_URL": settings.HELP_SUPPORT_URL,
            }
        }
        return instance
