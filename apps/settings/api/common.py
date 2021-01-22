# -*- coding: utf-8 -*-
#

from smtplib import SMTPSenderRefused
from rest_framework import generics
from rest_framework.views import Response, APIView
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
        if serializer.is_valid():
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
                resp = e.smtp_error
                if isinstance(resp, bytes):
                    for coding in ('gbk', 'utf8'):
                        try:
                            resp = resp.decode(coding)
                        except UnicodeDecodeError:
                            continue
                        else:
                            break
                return Response({"error": str(resp)}, status=400)
            except Exception as e:
                print(e)
                return Response({"error": str(e)}, status=400)
            return Response({"msg": self.success_message.format(email_recipient)})
        else:
            return Response({"error": str(serializer.errors)}, status=400)


class PublicSettingApi(generics.RetrieveAPIView):
    permission_classes = ()
    serializer_class = serializers.PublicSettingSerializer

    def get_object(self):
        instance = {
            "data": {
                "WINDOWS_SKIP_ALL_MANUAL_PASSWORD": settings.WINDOWS_SKIP_ALL_MANUAL_PASSWORD,
                "SECURITY_MAX_IDLE_TIME": settings.SECURITY_MAX_IDLE_TIME,
                "XPACK_ENABLED": settings.XPACK_ENABLED,
                "XPACK_LICENSE_IS_VALID": settings.XPACK_LICENSE_IS_VALID,
                "LOGIN_CONFIRM_ENABLE": settings.LOGIN_CONFIRM_ENABLE,
                "SECURITY_VIEW_AUTH_NEED_MFA": settings.SECURITY_VIEW_AUTH_NEED_MFA,
                "SECURITY_MFA_VERIFY_TTL": settings.SECURITY_MFA_VERIFY_TTL,
                "SECURITY_COMMAND_EXECUTION": settings.SECURITY_COMMAND_EXECUTION,
                "LOGIN_TITLE": settings.XPACK_INTERFACE_LOGIN_TITLE,
                "SECURITY_PASSWORD_EXPIRATION_TIME": settings.SECURITY_PASSWORD_EXPIRATION_TIME,
                "LOGO_URLS": {'logo_logout': static('img/logo.png'),
                              'logo_index': static('img/logo_text.png'),
                              'login_image': static('img/login_image.png'),
                              'favicon': static('img/facio.ico')},
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
