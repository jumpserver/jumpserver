from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.templatetags.static import static

from jumpserver.utils import has_valid_xpack_license
from common.utils import get_logger
from .. import serializers

logger = get_logger(__name__)

__all__ = ['PublicSettingApi']


class PublicSettingApi(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @staticmethod
    def get_logo_urls():
        logo_urls = {
            'logo_logout': static('img/logo.png'),
            'logo_index': static('img/logo_text.png'),
            'login_image': static('img/login_image.jpg'),
            'favicon': static('img/facio.ico')
        }
        if not settings.XPACK_ENABLED:
            return logo_urls
        from xpack.plugins.interface.models import Interface
        obj = Interface.interface()
        if not obj:
            return logo_urls
        for attr in ['logo_logout', 'logo_index', 'login_image', 'favicon']:
            if getattr(obj, attr, '') and getattr(obj, attr).url:
                logo_urls.update({attr: getattr(obj, attr).url})
        return logo_urls

    @staticmethod
    def get_login_title():
        default_title = _('Welcome to the JumpServer open source Bastion Host')
        if not settings.XPACK_ENABLED:
            return default_title
        from xpack.plugins.interface.models import Interface
        return Interface.get_login_title()

    def get_object(self):
        instance = {
            "data": {
                "WINDOWS_SKIP_ALL_MANUAL_PASSWORD": settings.WINDOWS_SKIP_ALL_MANUAL_PASSWORD,
                "SECURITY_MAX_IDLE_TIME": settings.SECURITY_MAX_IDLE_TIME,
                "XPACK_ENABLED": settings.XPACK_ENABLED,
                "LOGIN_CONFIRM_ENABLE": settings.LOGIN_CONFIRM_ENABLE,
                "SECURITY_VIEW_AUTH_NEED_MFA": settings.SECURITY_VIEW_AUTH_NEED_MFA,
                "SECURITY_MFA_VERIFY_TTL": settings.SECURITY_MFA_VERIFY_TTL,
                "OLD_PASSWORD_HISTORY_LIMIT_COUNT": settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT,
                "SECURITY_COMMAND_EXECUTION": settings.SECURITY_COMMAND_EXECUTION,
                "SECURITY_PASSWORD_EXPIRATION_TIME": settings.SECURITY_PASSWORD_EXPIRATION_TIME,
                "SECURITY_LUNA_REMEMBER_AUTH": settings.SECURITY_LUNA_REMEMBER_AUTH,
                "XPACK_LICENSE_IS_VALID": has_valid_xpack_license(),
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
            }
        }
        return instance
