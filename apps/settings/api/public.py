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
                # Security
                "WINDOWS_SKIP_ALL_MANUAL_PASSWORD": settings.WINDOWS_SKIP_ALL_MANUAL_PASSWORD,
                "OLD_PASSWORD_HISTORY_LIMIT_COUNT": settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT,
                "SECURITY_MAX_IDLE_TIME": settings.SECURITY_MAX_IDLE_TIME,
                "SECURITY_VIEW_AUTH_NEED_MFA": settings.SECURITY_VIEW_AUTH_NEED_MFA,
                "SECURITY_MFA_VERIFY_TTL": settings.SECURITY_MFA_VERIFY_TTL,
                "SECURITY_COMMAND_EXECUTION": settings.SECURITY_COMMAND_EXECUTION,
                "SECURITY_PASSWORD_EXPIRATION_TIME": settings.SECURITY_PASSWORD_EXPIRATION_TIME,
                "SECURITY_LUNA_REMEMBER_AUTH": settings.SECURITY_LUNA_REMEMBER_AUTH,
                "PASSWORD_RULE": {
                    'SECURITY_PASSWORD_MIN_LENGTH': settings.SECURITY_PASSWORD_MIN_LENGTH,
                    'SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH': settings.SECURITY_ADMIN_USER_PASSWORD_MIN_LENGTH,
                    'SECURITY_PASSWORD_UPPER_CASE': settings.SECURITY_PASSWORD_UPPER_CASE,
                    'SECURITY_PASSWORD_LOWER_CASE': settings.SECURITY_PASSWORD_LOWER_CASE,
                    'SECURITY_PASSWORD_NUMBER': settings.SECURITY_PASSWORD_NUMBER,
                    'SECURITY_PASSWORD_SPECIAL_CHAR': settings.SECURITY_PASSWORD_SPECIAL_CHAR,
                },
                'SECURITY_WATERMARK_ENABLED': settings.SECURITY_WATERMARK_ENABLED,
                'SECURITY_SESSION_SHARE': settings.SECURITY_SESSION_SHARE,
                # XPACK
                "XPACK_ENABLED": settings.XPACK_ENABLED,
                "XPACK_LICENSE_IS_VALID": has_valid_xpack_license(),
                "XPACK_LICENSE_INFO": get_xpack_license_info(),
                # Performance
                "LOGIN_TITLE": self.get_login_title(),
                "LOGO_URLS": self.get_logo_urls(),
                "HELP_DOCUMENT_URL": settings.HELP_DOCUMENT_URL,
                "HELP_SUPPORT_URL": settings.HELP_SUPPORT_URL,
                # Auth
                "AUTH_WECOM": settings.AUTH_WECOM,
                "AUTH_DINGTALK": settings.AUTH_DINGTALK,
                "AUTH_FEISHU": settings.AUTH_FEISHU,
                # Terminal
                "XRDP_ENABLED": settings.XRDP_ENABLED,
                "TERMINAL_KOKO_HOST": settings.TERMINAL_KOKO_HOST,
                "TERMINAL_KOKO_SSH_PORT": settings.TERMINAL_KOKO_SSH_PORT,
                "TERMINAL_MAGNUS_ENABLED": settings.TERMINAL_MAGNUS_ENABLED,
                "TERMINAL_MAGNUS_HOST": settings.TERMINAL_MAGNUS_HOST,
                "TERMINAL_MAGNUS_MYSQL_PORT": settings.TERMINAL_MAGNUS_MYSQL_PORT,
                "TERMINAL_MAGNUS_MARIADB_PORT": settings.TERMINAL_MAGNUS_MARIADB_PORT,
                "TERMINAL_MAGNUS_POSTGRE_PORT": settings.TERMINAL_MAGNUS_POSTGRE_PORT,
                # Announcement
                "ANNOUNCEMENT_ENABLED": settings.ANNOUNCEMENT_ENABLED,
                "ANNOUNCEMENT": settings.ANNOUNCEMENT,
            }
        }
        return instance
