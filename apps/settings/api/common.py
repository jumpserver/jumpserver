# -*- coding: utf-8 -*-
#

from smtplib import SMTPSenderRefused
from rest_framework import generics
from rest_framework.views import Response, APIView
from rest_framework.permissions import AllowAny
from django.conf import settings
from django.core.mail import send_mail, get_connection
from django.utils.translation import ugettext_lazy as _
from django.templatetags.static import static

from common.permissions import IsSuperUser
from common.utils import get_logger
from .. import serializers
from ..models import Setting

logger = get_logger(__file__)


class MailTestingAPI(APIView):
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.MailTestSerializer
    success_message = _("Test mail sent to {}, please check")

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        email_host = serializer.validated_data['EMAIL_HOST']
        email_port = serializer.validated_data['EMAIL_PORT']
        email_host_user = serializer.validated_data["EMAIL_HOST_USER"]
        email_host_password = serializer.validated_data['EMAIL_HOST_PASSWORD']
        email_from = serializer.validated_data["EMAIL_FROM"]
        email_recipient = serializer.validated_data["EMAIL_RECIPIENT"]
        email_use_ssl = serializer.validated_data['EMAIL_USE_SSL']
        email_use_tls = serializer.validated_data['EMAIL_USE_TLS']

        # 设置 settings 的值，会导致动态配置在当前进程失效
        # for k, v in serializer.validated_data.items():
        #     if k.startswith('EMAIL'):
        #         setattr(settings, k, v)
        try:
            subject = "Test"
            message = "Test smtp setting"
            email_from = email_from or email_host_user
            email_recipient = email_recipient or email_from
            connection = get_connection(
                host=email_host, port=email_port,
                username=email_host_user, password=email_host_password,
                use_tls=email_use_tls, use_ssl=email_use_ssl,
            )
            send_mail(
                subject, message, email_from, [email_recipient],
                connection=connection
            )
        except SMTPSenderRefused as e:
            error = e.smtp_error
            if isinstance(error, bytes):
                for coding in ('gbk', 'utf8'):
                    try:
                        error = error.decode(coding)
                    except UnicodeDecodeError:
                        continue
                    else:
                        break
            return Response({"error": str(error)}, status=400)
        except Exception as e:
            logger.error(e)
            return Response({"error": str(e)}, status=400)
        return Response({"msg": self.success_message.format(email_recipient)})


class PublicSettingApi(generics.RetrieveAPIView):
    permission_classes = (AllowAny,)
    serializer_class = serializers.PublicSettingSerializer

    @staticmethod
    def get_logo_urls():
        logo_urls = {
            'logo_logout': static('img/logo.png'),
            'logo_index': static('img/logo_text.png'),
            'login_image': static('img/login_image.png'),
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
    def get_xpack_license_is_valid():
        if not settings.XPACK_ENABLED:
            return False
        try:
            from xpack.plugins.license.models import License
            return License.has_valid_license()
        except Exception as e:
            logger.error(e)
            return False

    @staticmethod
    def get_login_title():
        default_title = _('Welcome to the JumpServer open source fortress')
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
                "SECURITY_COMMAND_EXECUTION": settings.SECURITY_COMMAND_EXECUTION,
                "SECURITY_PASSWORD_EXPIRATION_TIME": settings.SECURITY_PASSWORD_EXPIRATION_TIME,
                "XPACK_LICENSE_IS_VALID": self.get_xpack_license_is_valid(),
                "LOGIN_TITLE": self.get_login_title(),
                "LOGO_URLS": self.get_logo_urls(),
                "TICKETS_ENABLED": settings.TICKETS_ENABLED,
                "PASSWORD_RULE": {
                    'SECURITY_PASSWORD_MIN_LENGTH': settings.SECURITY_PASSWORD_MIN_LENGTH,
                    'SECURITY_PASSWORD_UPPER_CASE': settings.SECURITY_PASSWORD_UPPER_CASE,
                    'SECURITY_PASSWORD_LOWER_CASE': settings.SECURITY_PASSWORD_LOWER_CASE,
                    'SECURITY_PASSWORD_NUMBER': settings.SECURITY_PASSWORD_NUMBER,
                    'SECURITY_PASSWORD_SPECIAL_CHAR': settings.SECURITY_PASSWORD_SPECIAL_CHAR,
                }
            }
        }
        return instance


class SettingsApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsSuperUser,)
    serializer_class_mapper = {
        'all': serializers.SettingsSerializer,
        'basic': serializers.BasicSettingSerializer,
        'terminal': serializers.TerminalSettingSerializer,
        'security': serializers.SecuritySettingSerializer,
        'ldap': serializers.LDAPSettingSerializer,
        'email': serializers.EmailSettingSerializer,
        'email_content': serializers.EmailContentSettingSerializer,
    }

    def get_serializer_class(self):
        category = self.request.query_params.get('category', serializers.BasicSettingSerializer)
        return self.serializer_class_mapper.get(category, serializers.BasicSettingSerializer)

    def get_fields(self):
        serializer = self.get_serializer_class()()
        fields = serializer.get_fields()
        return fields

    def get_object(self):
        items = self.get_fields().keys()
        return {item: getattr(settings, item) for item in items}

    def parse_serializer_data(self, serializer):
        data = []
        fields = self.get_fields()
        encrypted_items = [name for name, field in fields.items() if field.write_only]
        category = self.request.query_params.get('category', '')
        for name, value in serializer.validated_data.items():
            encrypted = name in encrypted_items
            data.append({
                'name': name, 'value': value,
                'encrypted': encrypted, 'category': category
            })
        return data

    def perform_update(self, serializer):
        settings_items = self.parse_serializer_data(serializer)
        serializer_data = getattr(serializer, 'data', {})
        for item in settings_items:
            changed, setting = Setting.update_or_create(**item)
            if not changed:
                continue
            serializer_data[setting.name] = setting.cleaned_value
        setattr(serializer, '_data', serializer_data)
